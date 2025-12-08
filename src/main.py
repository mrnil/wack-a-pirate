# src/main.py
import sys
import os
import pygame
from .app import GameApp 
from . import config

def main():
    """Application entry point."""
    
    # Simple check for asset folder
    # FIX: Use the new internal path resolver to check the location relative to the project root
    if not os.path.isdir(config._resolve_path(config.ASSET_PATH)):
        print(f"Error: Asset directory not found. Please ensure the folder is located at '<project_root>/assets/{config.ASSET_PATH}' relative to 'src'.")
        sys.exit(1)
        
    try:
        app = GameApp()
        app.run()
    except Exception as e:
        print(f"A fatal error occurred: {e}")
        # Ensure cleanup is attempted even if the app failed to initialize fully
        if 'app' in locals():
            app.shutdown() 
        sys.exit(1)

if __name__ == "__main__":
    main()