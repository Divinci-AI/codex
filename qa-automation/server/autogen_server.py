#!/usr/bin/env python3
"""
AutoGen Server for Codex Lifecycle Hook Integration

This server receives lifecycle events from Codex CLI via webhooks and
coordinates with the Magentic-One QA system to perform automated testing
and validation.
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid
import threading
import queue
import time

# FastAPI for the webhook server
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# Add the agents directory to the path
sys.path.append(str(Path(__file__).parent.parent / "agents"))
sys.path.append(str(Path(__file__).parent.parent / "safety"))

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from integrated_qa_system import IntegratedCodexHooksQASystem
    from safety_integration import SafetyIntegrationSystem
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    # Create mock classes for testing
    class OpenAIChatCompletionClient:
        def __init__(self, model, api_key):
            self.model = model
            self.api_key = api_key
        async def close(self):
            pass
    
    class IntegratedCodexHooksQASystem:
        def __init__(self, model_client):
            self.model_client = model_client
        async def cleanup(self):
            pass
    
    class SafetyIntegrationSystem:
        def __init__(self, security_level="standard", **kwargs):
            self.security_level = security_level

logger = logging.getLogger(__name__)


class CodexAutoGenServer:
    """
    AutoGen Server that receives Codex lifecycle events and coordinates
    with the Magentic-One QA system for automated testing and validation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._load_default_config()
        self.app = FastAPI(title="Codex AutoGen Server", version="1.0.0")
        
        # Initialize components
        self.model_client = None
        self.qa_system = None
        self.safety_system = None
        self.active_sessions = {}
        self.event_queue = queue.Queue()
        self.processing_thread = None
        
        # Server state
        self.is_running = False
        self.startup_time = None
        
        # Setup routes and initialize
        self._setup_routes()
        self._setup_logging()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default server configuration."""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False,
                "workers": 1
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": "gpt-4o",
                "timeout": 30
            },
            "qa_system": {
                "enabled": True,
                "auto_run": True,
                "safety_level": "standard"
            },
            "webhook": {
                "timeout": 60,
                "max_retries": 3
            }
        }
        
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('qa-automation/logs/autogen_server.log')
            ]
        )
        
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.on_event("startup")
        async def startup_event():
            await self._initialize_systems()
            
        @self.app.on_event("shutdown")
        async def shutdown_event():
            await self._cleanup_systems()
            
        @self.app.get("/")
        async def root():
            return {
                "service": "Codex AutoGen Server",
                "version": "1.0.0",
                "status": "running" if self.is_running else "starting",
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
            }
            
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            health_status = {
                "status": "healthy" if self.is_running else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "qa_system": self.qa_system is not None,
                    "safety_system": self.safety_system is not None,
                    "model_client": self.model_client is not None
                },
                "active_sessions": len(self.active_sessions),
                "queue_size": self.event_queue.qsize()
            }
            
            if not self.is_running:
                raise HTTPException(status_code=503, detail="Server not ready")
                
            return health_status
            
        @self.app.post("/webhook/codex")
        async def handle_codex_webhook(request: Request, background_tasks: BackgroundTasks):
            """
            Main webhook endpoint for receiving Codex lifecycle events.
            """
            try:
                # Parse the incoming event
                event_data = await request.json()
                
                # Validate event structure
                if not self._validate_event_data(event_data):
                    raise HTTPException(status_code=400, detail="Invalid event data structure")
                
                # Generate event ID
                event_id = str(uuid.uuid4())
                event_data["event_id"] = event_id
                event_data["received_at"] = datetime.now().isoformat()
                
                logger.info(f"Received Codex event: {event_data.get('eventType', 'unknown')} (ID: {event_id})")
                
                # Queue event for processing
                self.event_queue.put(event_data)
                
                # Process event in background
                background_tasks.add_task(self._process_codex_event, event_data)
                
                return {
                    "status": "received",
                    "event_id": event_id,
                    "message": "Event queued for processing",
                    "timestamp": datetime.now().isoformat()
                }
                
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
            except Exception as e:
                logger.error(f"Error handling Codex webhook: {e}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
                
        @self.app.get("/sessions")
        async def get_active_sessions():
            """Get information about active sessions."""
            return {
                "active_sessions": len(self.active_sessions),
                "sessions": [
                    {
                        "session_id": sid,
                        "status": session.get("status", "unknown"),
                        "event_type": session.get("event_type", "unknown"),
                        "started_at": session.get("started_at"),
                        "last_activity": session.get("last_activity")
                    }
                    for sid, session in self.active_sessions.items()
                ]
            }
            
        @self.app.get("/sessions/{session_id}")
        async def get_session_details(session_id: str):
            """Get detailed information about a specific session."""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
                
            return self.active_sessions[session_id]
            
        @self.app.delete("/sessions/{session_id}")
        async def cleanup_session(session_id: str):
            """Manually cleanup a session."""
            if session_id not in self.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
                
            await self._cleanup_session(session_id)
            return {"status": "cleaned_up", "session_id": session_id}
            
    async def _initialize_systems(self):
        """Initialize the QA and safety systems."""
        logger.info("Initializing AutoGen server systems...")
        
        try:
            # Initialize OpenAI client
            api_key = self.config["openai"]["api_key"]
            if not api_key:
                logger.warning("OpenAI API key not configured - using mock client")
                
            self.model_client = OpenAIChatCompletionClient(
                model=self.config["openai"]["model"],
                api_key=api_key or "mock-key"
            )
            
            # Initialize QA system
            if self.config["qa_system"]["enabled"]:
                self.qa_system = IntegratedCodexHooksQASystem(self.model_client)
                logger.info("QA system initialized")
                
            # Initialize safety system
            self.safety_system = SafetyIntegrationSystem(
                security_level=self.config["qa_system"]["safety_level"],
                enable_container_isolation=False,  # Disable for server mode
                enable_human_oversight=False
            )
            logger.info("Safety system initialized")
            
            self.is_running = True
            self.startup_time = datetime.now()
            
            logger.info("AutoGen server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize systems: {e}")
            raise
            
    async def _cleanup_systems(self):
        """Cleanup systems on shutdown."""
        logger.info("Shutting down AutoGen server...")
        
        self.is_running = False
        
        # Cleanup active sessions
        for session_id in list(self.active_sessions.keys()):
            await self._cleanup_session(session_id)
            
        # Cleanup systems
        if self.qa_system:
            await self.qa_system.cleanup()
            
        if self.model_client:
            await self.model_client.close()
            
        logger.info("AutoGen server shutdown complete")
        
    def _validate_event_data(self, event_data: Dict[str, Any]) -> bool:
        """Validate the structure of incoming event data."""
        required_fields = ["eventType", "sessionId", "timestamp"]
        
        for field in required_fields:
            if field not in event_data:
                logger.warning(f"Missing required field: {field}")
                return False
                
        return True
        
    async def _process_codex_event(self, event_data: Dict[str, Any]):
        """Process a Codex lifecycle event."""
        event_id = event_data["event_id"]
        event_type = event_data["eventType"]
        session_id = event_data["sessionId"]
        
        logger.info(f"Processing Codex event: {event_type} (Session: {session_id})")
        
        try:
            # Create or update session
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = {
                    "session_id": session_id,
                    "started_at": datetime.now().isoformat(),
                    "events": [],
                    "status": "active"
                }
                
            session = self.active_sessions[session_id]
            session["events"].append(event_data)
            session["last_activity"] = datetime.now().isoformat()
            session["event_type"] = event_type
            session["status"] = "processed"
                
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}")
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["status"] = "error"
                self.active_sessions[session_id]["error"] = str(e)
                
    async def _cleanup_session(self, session_id: str):
        """Cleanup a session and its resources."""
        
        if session_id in self.active_sessions:
            # Remove from active sessions
            del self.active_sessions[session_id]
            logger.info(f"Session cleaned up: {session_id}")
        
    def run(self):
        """Run the AutoGen server."""
        
        server_config = self.config["server"]
        
        logger.info(f"Starting AutoGen server on {server_config['host']}:{server_config['port']}")
        
        uvicorn.run(
            self.app,
            host=server_config["host"],
            port=server_config["port"],
            log_level="info" if server_config["debug"] else "warning",
            workers=server_config["workers"]
        )


def main():
    """Main entry point for the AutoGen server."""
    
    # Load configuration
    config_file = os.getenv("AUTOGEN_CONFIG", "qa-automation/config/autogen-server.json")
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = None
        
    # Create and run server
    server = CodexAutoGenServer(config)
    server.run()


if __name__ == "__main__":
    main()
