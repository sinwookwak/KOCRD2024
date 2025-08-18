#!/usr/bin/env python3
"""
Test script to verify that all import paths are correct
"""
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

def test_imports():
    """Test critical import paths"""
    print("Testing critical imports...")
    
    try:
        # Test config imports
        from kocrd.config.config import text_manager, AppConfig
        print("✓ Config imports successful")
    except ImportError as e:
        print(f"✗ Config import failed: {e}")
        
    try:
        # Test settings manager import
        from kocrd.setting.settings_manager import SettingsManager
        print("✓ Settings manager import successful")
    except ImportError as e:
        print(f"✗ Settings manager import failed: {e}")
        
    try:
        # Test system manager import
        from kocrd.managers.system_manager import SystemManager
        print("✓ System manager import successful")
    except ImportError as e:
        print(f"✗ System manager import failed: {e}")
        
    try:
        # Test database manager import
        from kocrd.managers.database_manager import DatabaseManager
        print("✓ Database manager import successful")
    except ImportError as e:
        print(f"✗ Database manager import failed: {e}")
        
    try:
        # Test window imports
        from kocrd.window.main_window import MainWindow
        print("✓ Main window import successful")
    except ImportError as e:
        print(f"✗ Main window import failed: {e}")
        
    try:
        # Test AI manager imports
        from kocrd.managers.ai_managers.AI_model_manager import AIModelManager
        print("✓ AI model manager import successful")
    except ImportError as e:
        print(f"✗ AI model manager import failed: {e}")
        
    try:
        # Test utils imports
        from kocrd.utils.embedding_utils import EmbeddingUtils
        print("✓ Embedding utils import successful")
    except ImportError as e:
        print(f"✗ Embedding utils import failed: {e}")

    print("\nImport testing complete!")

if __name__ == "__main__":
    test_imports()