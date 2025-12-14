# src/sprite_sheet.py
import pygame
import xml.etree.ElementTree as ET
from typing import Dict, Tuple, Optional
from .logger import setup_logger
from .exceptions import AssetError
from . import config

class SpriteSheet:
    """Manages sprite sheet loading and sprite extraction."""
    
    def __init__(self, sheet_path: str, xml_path: str):
        self.logger = setup_logger()
        self.sheet_path = sheet_path
        self.xml_path = xml_path
        self.sheet_surface: Optional[pygame.Surface] = None
        self.sprite_data: Dict[str, Tuple[int, int, int, int]] = {}
        self._sprite_cache: Dict[str, pygame.Surface] = {}
        
    def load(self) -> bool:
        """Load the sprite sheet and parse XML data."""
        try:
            # Load sprite sheet image
            full_sheet_path = config._resolve_path(f"kenney_pirate-pack (1)/Spritesheet/{self.sheet_path}")
            self.sheet_surface = pygame.image.load(full_sheet_path).convert_alpha()
            
            # Parse XML data
            full_xml_path = config._resolve_path(f"kenney_pirate-pack (1)/Spritesheet/{self.xml_path}")
            tree = ET.parse(full_xml_path)
            root = tree.getroot()
            
            # Extract sprite coordinates
            for subtexture in root.findall('SubTexture'):
                name = subtexture.get('name')
                x = int(subtexture.get('x'))
                y = int(subtexture.get('y'))
                width = int(subtexture.get('width'))
                height = int(subtexture.get('height'))
                self.sprite_data[name] = (x, y, width, height)
            
            self.logger.info(f"Loaded sprite sheet with {len(self.sprite_data)} sprites")
            return True
            
        except (pygame.error, ET.ParseError, FileNotFoundError) as e:
            self.logger.error(f"Failed to load sprite sheet: {e}")
            raise AssetError(f"Sprite sheet loading failed: {e}")
    
    def get_sprite(self, name: str, scale: float = 1.0) -> pygame.Surface:
        """Extract and cache a sprite from the sheet."""
        cache_key = f"{name}_{scale}"
        
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]
        
        if name not in self.sprite_data:
            self.logger.warning(f"Sprite '{name}' not found in sheet")
            # Return fallback sprite
            fallback = pygame.Surface((50, 50))
            fallback.fill((100, 100, 100))
            return fallback
        
        x, y, width, height = self.sprite_data[name]
        
        # Extract sprite from sheet
        sprite_rect = pygame.Rect(x, y, width, height)
        sprite_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        sprite_surface.blit(self.sheet_surface, (0, 0), sprite_rect)
        
        # Scale if needed
        if scale != 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            sprite_surface = pygame.transform.scale(sprite_surface, (new_width, new_height))
        
        # Cache the sprite
        self._sprite_cache[cache_key] = sprite_surface
        return sprite_surface
    
    def clear_cache(self):
        """Clear sprite cache to free memory."""
        self._sprite_cache.clear()
        self.logger.debug("Sprite cache cleared")

class SpriteManager:
    """Global sprite sheet manager."""
    
    def __init__(self):
        self.logger = setup_logger()
        self.sheets: Dict[str, SpriteSheet] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize all sprite sheets."""
        if self._initialized:
            return
        
        try:
            # Load main ship sprite sheet
            ship_sheet = SpriteSheet("shipsMiscellaneous_sheet@2.png", "shipsMiscellaneous_sheet@2.xml")
            ship_sheet.load()
            self.sheets['ships'] = ship_sheet
            
            self._initialized = True
            self.logger.info("Sprite manager initialized")
            
        except AssetError as e:
            self.logger.warning(f"Failed to load retina sprites, trying standard: {e}")
            try:
                # Fallback to standard resolution
                ship_sheet = SpriteSheet("shipsMiscellaneous_sheet.png", "shipsMiscellaneous_sheet.xml")
                ship_sheet.load()
                self.sheets['ships'] = ship_sheet
                self._initialized = True
                self.logger.info("Sprite manager initialized with standard resolution")
            except AssetError:
                self.logger.error("Failed to initialize sprite manager")
                raise
    
    def get_sprite(self, sheet_name: str, sprite_name: str, scale: float = 0.75) -> pygame.Surface:
        """Get a sprite from a specific sheet."""
        if not self._initialized:
            self.initialize()
        
        if sheet_name not in self.sheets:
            raise AssetError(f"Sprite sheet '{sheet_name}' not found")
        
        return self.sheets[sheet_name].get_sprite(sprite_name, scale)
    
    def cleanup(self):
        """Clean up all sprite sheets and caches."""
        for sheet in self.sheets.values():
            sheet.clear_cache()
        self.sheets.clear()
        self._initialized = False
        self.logger.info("Sprite manager cleaned up")

# Global sprite manager instance
sprite_manager = SpriteManager()