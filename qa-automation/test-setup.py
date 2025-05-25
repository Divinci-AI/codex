#!/usr/bin/env python3
"""
Quick setup test for Magentic-One QA Automation

This script tests that all dependencies are properly installed and configured.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing package imports...")
    
    try:
        import autogen_agentchat
        print("✓ autogen-agentchat imported successfully")
    except ImportError as e:
        print(f"✗ autogen-agentchat import failed: {e}")
        return False
    
    try:
        import autogen_ext
        print("✓ autogen-ext imported successfully")
    except ImportError as e:
        print(f"✗ autogen-ext import failed: {e}")
        return False
    
    try:
        from playwright.sync_api import sync_playwright
        print("✓ playwright imported successfully")
    except ImportError as e:
        print(f"✗ playwright import failed: {e}")
        return False
    
    try:
        import toml
        print("✓ toml imported successfully")
    except ImportError as e:
        print(f"✗ toml import failed: {e}")
        return False
    
    return True

def test_configuration():
    """Test that configuration files exist and are valid."""
    print("\nTesting configuration...")
    
    config_file = Path("qa-automation/config/qa-config.toml")
    if not config_file.exists():
        print(f"✗ Configuration file not found: {config_file}")
        return False
    
    try:
        import toml
        with open(config_file, 'r') as f:
            config = toml.load(f)
        print("✓ Configuration file loaded successfully")
        
        # Check required sections
        required_sections = ['qa', 'openai', 'agents', 'safety']
        for section in required_sections:
            if section not in config:
                print(f"✗ Missing required section: {section}")
                return False
            print(f"✓ Found required section: {section}")
        
    except Exception as e:
        print(f"✗ Configuration file validation failed: {e}")
        return False
    
    return True

def test_environment():
    """Test environment setup."""
    print("\nTesting environment...")
    
    # Check if we're in the right directory
    if not Path("qa-automation").exists():
        print("✗ qa-automation directory not found. Are you in the project root?")
        return False
    print("✓ qa-automation directory found")
    
    # Check required directories
    required_dirs = [
        "qa-automation/config",
        "qa-automation/magentic-one", 
        "qa-automation/agents",
        "qa-automation/scripts"
    ]
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            print(f"✗ Required directory not found: {dir_path}")
            return False
        print(f"✓ Found required directory: {dir_path}")
    
    return True

def test_openai_config():
    """Test OpenAI configuration."""
    print("\nTesting OpenAI configuration...")
    
    # Check if .env file exists
    env_file = Path("qa-automation/config/.env")
    if env_file.exists():
        print("✓ Environment file found")
        
        # Load environment variables
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        except Exception as e:
            print(f"✗ Failed to load environment file: {e}")
            return False
    else:
        print("⚠ Environment file not found (using system environment)")
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print("✓ OPENAI_API_KEY found in environment")
        if api_key.startswith('sk-'):
            print("✓ API key format looks correct")
        else:
            print("⚠ API key format may be incorrect")
    else:
        print("⚠ OPENAI_API_KEY not found in environment")
        print("  Please set your OpenAI API key in qa-automation/config/.env")
    
    return True

def test_magentic_one_basic():
    """Test basic Magentic-One functionality."""
    print("\nTesting Magentic-One basic functionality...")
    
    try:
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        print("✓ OpenAI client import successful")
    except ImportError as e:
        print(f"✗ OpenAI client import failed: {e}")
        return False
    
    try:
        from autogen_ext.teams.magentic_one import MagenticOne
        print("✓ MagenticOne import successful")
    except ImportError as e:
        print(f"✗ MagenticOne import failed: {e}")
        return False
    
    try:
        from autogen_ext.agents.file_surfer import FileSurfer
        from autogen_ext.agents.web_surfer import MultimodalWebSurfer
        from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
        print("✓ Individual agents import successful")
    except ImportError as e:
        print(f"✗ Individual agents import failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("Magentic-One QA Automation Setup Test")
    print("=" * 50)
    
    tests = [
        ("Package Imports", test_imports),
        ("Configuration", test_configuration),
        ("Environment", test_environment),
        ("OpenAI Config", test_openai_config),
        ("Magentic-One Basic", test_magentic_one_basic)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"✗ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Magentic-One QA setup is ready.")
        print("\nNext steps:")
        print("1. Set your OpenAI API key in qa-automation/config/.env")
        print("2. Run: python qa-automation/magentic-one/qa_orchestrator.py")
        print("3. Or use: ./qa-automation/scripts/run-qa.sh")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nTroubleshooting:")
        print("1. Run: ./qa-automation/scripts/setup.sh")
        print("2. Check that you're in the project root directory")
        print("3. Ensure all dependencies are installed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
