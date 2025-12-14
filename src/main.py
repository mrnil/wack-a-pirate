# src/main.py
import sys
import os
import pygame
from .app import GameApp 
from . import config
from .logger import setup_logger
from .exceptions import GameError, AssetError, ConfigError

def main():
    """Application entry point."""
    logger = setup_logger()
    
    try:
        # Validate configuration
        config.validate_config()
        
        # Validate asset directory
        if not os.path.isdir(config._resolve_path(config.ASSET_PATH)):
            raise AssetError(f"Asset directory not found: {config.ASSET_PATH}")
        
        logger.info("Starting Whack-A-Pirate Battle")
        app = GameApp()
        app.run()
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except AssetError as e:
        logger.error(f"Asset error: {e}")
        sys.exit(1)
    except GameError as e:
        logger.error(f"Game error: {e}")
        if 'app' in locals():
            app.shutdown()
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Game interrupted by user")
        if 'app' in locals():
            app.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        if 'app' in locals():
            app.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    main()