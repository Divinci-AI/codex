#!/usr/bin/env python3
"""
Performance Metrics Hook
This script tracks performance metrics for Codex operations
"""

import os
import json
import time
import psutil
from datetime import datetime
from pathlib import Path

# Configuration
ANALYTICS_DIR = Path.home() / '.codex' / 'analytics'
METRICS_FILE = ANALYTICS_DIR / 'performance-metrics.json'
DAILY_METRICS_FILE = ANALYTICS_DIR / f'metrics-{datetime.now().strftime("%Y-%m-%d")}.json'

# Ensure analytics directory exists
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

def get_system_metrics():
    """Get current system performance metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024**3),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error getting system metrics: {e}")
        return None

def load_metrics_file(file_path):
    """Load metrics from file or create new structure"""
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading {file_path}: {e}")
    
    return {
        'sessions': {},
        'system_metrics': [],
        'performance_summary': {
            'avg_cpu_usage': 0,
            'avg_memory_usage': 0,
            'peak_cpu_usage': 0,
            'peak_memory_usage': 0,
            'total_measurements': 0
        }
    }

def save_metrics_file(file_path, data):
    """Save metrics to file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving {file_path}: {e}")

def track_session_start():
    """Track session start metrics"""
    session_id = os.getenv('CODEX_SESSION_ID', '')
    model = os.getenv('CODEX_MODEL', 'unknown')
    
    # Load daily metrics
    daily_metrics = load_metrics_file(DAILY_METRICS_FILE)
    
    # Get system metrics
    system_metrics = get_system_metrics()
    if not system_metrics:
        return
    
    # Initialize session tracking
    daily_metrics['sessions'][session_id] = {
        'start_time': datetime.now().isoformat(),
        'model': model,
        'start_metrics': system_metrics,
        'command_count': 0,
        'task_count': 0,
        'peak_cpu': system_metrics['cpu_percent'],
        'peak_memory': system_metrics['memory_percent'],
        'metrics_history': [system_metrics]
    }
    
    # Add to system metrics history
    daily_metrics['system_metrics'].append({
        'event': 'session_start',
        'session_id': session_id,
        **system_metrics
    })
    
    save_metrics_file(DAILY_METRICS_FILE, daily_metrics)
    print(f"📊 Performance tracking started for session {session_id}")
    print(f"   CPU: {system_metrics['cpu_percent']:.1f}%, Memory: {system_metrics['memory_percent']:.1f}%")

def track_session_end():
    """Track session end metrics"""
    session_id = os.getenv('CODEX_SESSION_ID', '')
    duration = os.getenv('CODEX_DURATION', '')
    
    # Load daily metrics
    daily_metrics = load_metrics_file(DAILY_METRICS_FILE)
    
    if session_id not in daily_metrics['sessions']:
        print(f"Warning: Session {session_id} not found in metrics")
        return
    
    # Get final system metrics
    system_metrics = get_system_metrics()
    if not system_metrics:
        return
    
    session_data = daily_metrics['sessions'][session_id]
    session_data['end_time'] = datetime.now().isoformat()
    session_data['end_metrics'] = system_metrics
    session_data['duration_ms'] = int(duration) if duration else None
    
    # Calculate session performance summary
    metrics_history = session_data['metrics_history']
    if metrics_history:
        avg_cpu = sum(m['cpu_percent'] for m in metrics_history) / len(metrics_history)
        avg_memory = sum(m['memory_percent'] for m in metrics_history) / len(metrics_history)
        
        session_data['performance_summary'] = {
            'avg_cpu': avg_cpu,
            'avg_memory': avg_memory,
            'peak_cpu': session_data['peak_cpu'],
            'peak_memory': session_data['peak_memory'],
            'measurements': len(metrics_history)
        }
    
    # Add to system metrics history
    daily_metrics['system_metrics'].append({
        'event': 'session_end',
        'session_id': session_id,
        **system_metrics
    })
    
    # Update overall performance summary
    update_performance_summary(daily_metrics)
    
    save_metrics_file(DAILY_METRICS_FILE, daily_metrics)
    
    # Also update the main metrics file
    update_main_metrics(session_data)
    
    print(f"📊 Performance tracking completed for session {session_id}")
    if 'performance_summary' in session_data:
        summary = session_data['performance_summary']
        print(f"   Avg CPU: {summary['avg_cpu']:.1f}%, Avg Memory: {summary['avg_memory']:.1f}%")
        print(f"   Peak CPU: {summary['peak_cpu']:.1f}%, Peak Memory: {summary['peak_memory']:.1f}%")

def track_command_start():
    """Track command start metrics"""
    session_id = os.getenv('CODEX_SESSION_ID', '')
    command = os.getenv('CODEX_COMMAND', '')
    
    # Load daily metrics
    daily_metrics = load_metrics_file(DAILY_METRICS_FILE)
    
    if session_id in daily_metrics['sessions']:
        daily_metrics['sessions'][session_id]['command_count'] += 1
        
        # Get current system metrics
        system_metrics = get_system_metrics()
        if system_metrics:
            # Update peak values
            session_data = daily_metrics['sessions'][session_id]
            session_data['peak_cpu'] = max(session_data['peak_cpu'], system_metrics['cpu_percent'])
            session_data['peak_memory'] = max(session_data['peak_memory'], system_metrics['memory_percent'])
            session_data['metrics_history'].append(system_metrics)
            
            # Add to system metrics history
            daily_metrics['system_metrics'].append({
                'event': 'command_start',
                'session_id': session_id,
                'command': command,
                **system_metrics
            })
        
        save_metrics_file(DAILY_METRICS_FILE, daily_metrics)

def track_task_start():
    """Track task start metrics"""
    session_id = os.getenv('CODEX_SESSION_ID', '')
    task_id = os.getenv('CODEX_TASK_ID', '')
    
    # Load daily metrics
    daily_metrics = load_metrics_file(DAILY_METRICS_FILE)
    
    if session_id in daily_metrics['sessions']:
        daily_metrics['sessions'][session_id]['task_count'] += 1
        
        # Get current system metrics
        system_metrics = get_system_metrics()
        if system_metrics:
            # Add to system metrics history
            daily_metrics['system_metrics'].append({
                'event': 'task_start',
                'session_id': session_id,
                'task_id': task_id,
                **system_metrics
            })
        
        save_metrics_file(DAILY_METRICS_FILE, daily_metrics)

def update_performance_summary(daily_metrics):
    """Update the daily performance summary"""
    all_metrics = daily_metrics['system_metrics']
    if not all_metrics:
        return
    
    cpu_values = [m['cpu_percent'] for m in all_metrics if 'cpu_percent' in m]
    memory_values = [m['memory_percent'] for m in all_metrics if 'memory_percent' in m]
    
    if cpu_values and memory_values:
        daily_metrics['performance_summary'] = {
            'avg_cpu_usage': sum(cpu_values) / len(cpu_values),
            'avg_memory_usage': sum(memory_values) / len(memory_values),
            'peak_cpu_usage': max(cpu_values),
            'peak_memory_usage': max(memory_values),
            'total_measurements': len(all_metrics)
        }

def update_main_metrics(session_data):
    """Update the main metrics file with session data"""
    main_metrics = load_metrics_file(METRICS_FILE)
    
    # Add session summary to main metrics
    session_id = session_data.get('start_time', datetime.now().isoformat())
    main_metrics['sessions'][session_id] = {
        'model': session_data.get('model'),
        'duration_ms': session_data.get('duration_ms'),
        'command_count': session_data.get('command_count', 0),
        'task_count': session_data.get('task_count', 0),
        'performance_summary': session_data.get('performance_summary', {})
    }
    
    save_metrics_file(METRICS_FILE, main_metrics)

def main():
    """Main function"""
    event_type = os.getenv('CODEX_EVENT_TYPE', '')
    
    if event_type == 'session_start':
        track_session_start()
    elif event_type == 'session_end':
        track_session_end()
    elif event_type == 'command_start':
        track_command_start()
    elif event_type == 'task_start':
        track_task_start()
    else:
        print(f"Performance metrics: Ignoring event type '{event_type}'")

if __name__ == "__main__":
    main()
