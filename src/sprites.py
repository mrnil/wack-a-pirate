# src/sprites.py
import pygame
import os
from . import config
from . import battle_logic
from .logger import setup_logger
from .exceptions import AssetError


class EnemyShip(pygame.sprite.Sprite):
    """Represents a single enemy ship with its health and visual properties."""
    def __init__(self, name, max_health, sprite_paths):
        super().__init__()
        self.name = name
        self.max_health = max_health
        self.current_health = max_health
        self.is_destroyed = False
        
        # Position is set later by battle_logic.initialize_fleet_structure
        self.battle_pos = None 
        
        # Pygame Image Handling (LOADED ONCE)
        self.images = {
            "full": self._load_and_scale(sprite_paths["full"]),
            "half": self._load_and_scale(sprite_paths["half"]),
            "destroyed": self._load_and_scale(sprite_paths["destroyed"]),
        }
        
        self.image = self.images["full"]
        self.rect = self.image.get_rect()

    def _load_and_scale(self, sprite_path):
        """Loads and scales a single image with error handling."""
        logger = setup_logger()
        full_path = config.resolve_asset_path(sprite_path)
        
        try:
            original_image = pygame.image.load(full_path).convert_alpha()
            scale_factor = 0.75
            new_size = (int(original_image.get_width() * scale_factor), 
                        int(original_image.get_height() * scale_factor))
            return pygame.transform.scale(original_image, new_size)
            
        except FileNotFoundError:
            logger.error(f"Ship sprite not found: {full_path}")
            raise AssetError(f"Missing ship sprite: {sprite_path}")
        except pygame.error as e:
            logger.error(f"Failed to load ship sprite {full_path}: {e}")
            # Return fallback sprite
            img = pygame.Surface((100, 100))
            img.fill((100, 100, 100))
            return img

    def get_current_sprite(self):
        """Returns the appropriate image based on current health status."""
        if self.is_destroyed:
            return self.images["destroyed"]
        
        health_ratio = self.current_health / self.max_health
        
        if health_ratio <= 0.5:
            return self.images["half"]
        
        return self.images["full"]

    def take_damage(self):
        """Reduces the ship's current health."""
        logger = setup_logger()
        
        if not self.is_destroyed:
            self.current_health -= 1
            self.image = self.get_current_sprite() 
            
            if self.current_health <= 0:
                self.is_destroyed = True
                logger.info(f"Ship destroyed: {self.name}")
                return "SHIP_DESTROYED"
            else:
                logger.debug(f"Ship hit: {self.name} ({self.current_health} HP remaining)")
                return "SHIP_HIT"
        return None

class Cannon(pygame.sprite.Sprite):
    """Represents the player's fortress/cannon, now centered."""
    def __init__(self):
        super().__init__()
        # Load cannon image
        logger = setup_logger()
        try:
            full_path = config.resolve_asset_path("Ships/ship (2).png")
            original_image = pygame.image.load(full_path).convert_alpha()
            scale_factor = 1
            new_size = (int(original_image.get_width() * scale_factor), int(original_image.get_height() * scale_factor))
            self.image = pygame.transform.scale(original_image, new_size)
        except (pygame.error, FileNotFoundError) as e:
            logger.warning(f"Failed to load cannon sprite: {e}, using fallback")
            self.image = pygame.Surface((50, 30))
            self.image.fill(config.WHITE)
            
        self.rect = self.image.get_rect(center=(battle_logic.SCREEN_WIDTH // 2, battle_logic.SCREEN_HEIGHT // 2))

    def update(self):
        # Update center in case of screen resize (handled by GameApp)
        self.rect.center = (battle_logic.SCREEN_WIDTH // 2, battle_logic.SCREEN_HEIGHT // 2)

    def draw_health_bar(self, screen, font):
        """Draws the Player's Fortress Health Bar at the top left."""
        MAX_WIDTH = 250
        BAR_HEIGHT = 20
        x, y = 10, 10 
        
        fortress = battle_logic.PLAYER_FORTRESS
        fill_ratio = max(0, fortress['health'] / fortress['max_health'])
        fill_width = MAX_WIDTH * fill_ratio
        
        # 1. Draw Health Bar
        border_rect = pygame.Rect(x, y, MAX_WIDTH, BAR_HEIGHT)
        pygame.draw.rect(screen, config.BLACK, border_rect, 2)
        
        color = config.GREEN
        if fill_ratio < 0.5: color = (255, 165, 0)
        if fill_ratio < 0.2: color = config.RED
            
        fill_rect = pygame.Rect(x, y, fill_width, BAR_HEIGHT)
        pygame.draw.rect(screen, color, fill_rect)

        # 2. Draw Text BELOW the bar
        text_content = f"FORTRESS HP: {fortress['health']:.1f}"
        
        # Calculate Y position: Below the bar (y + BAR_HEIGHT + padding)
        text_y_start = y + BAR_HEIGHT + 5 
        
        text = font.render(text_content, True, config.WHITE) 
        text_rect = text.get_rect(topleft=(x + 5, text_y_start))

        # Draw sheer background for the text
        sheer_text_surface = pygame.Surface(text_rect.size, pygame.SRCALPHA)
        sheer_text_surface.fill((0, 0, 0, 100)) # 100 is a slight transparency
        screen.blit(sheer_text_surface, text_rect.topleft)
        screen.blit(text, text_rect.topleft)

class Effect(pygame.sprite.Sprite):
    """Represents a cannonball in motion or a temporary explosion."""
    def __init__(self, start_pos, end_pos, effect_type, duration=None):
        super().__init__()
        self.effect_type = effect_type
        self.start_pos = pygame.Vector2(start_pos)
        self.end_pos = pygame.Vector2(end_pos)
        self.position = self.start_pos
        self.speed = 10 
        self.distance = self.end_pos - self.start_pos
        self.total_distance = self.distance.length()
        self.progress = 0.0
        self.is_moving = True
        
        if effect_type in ["HIT", "MISS"]:
            self.load_image("Ship parts/cannonBall.png", scale=1.0)
            if self.total_distance > 0:
                self.direction = self.distance.normalize()
        elif effect_type == "EXPLOSION":
            self.load_image("Effects/explosion1.png", scale=1.0)
            self.lifetime = duration if duration else 15 
            self.is_moving = False
            self.rect = self.image.get_rect(center=self.end_pos)
            
    def load_image(self, path, scale):
        logger = setup_logger()
        full_path = config.resolve_asset_path(path)
        
        try:
            original_image = pygame.image.load(full_path).convert_alpha()
            new_width = int(original_image.get_width() * scale)
            new_height = int(original_image.get_height() * scale)
            self.image = pygame.transform.scale(original_image, (new_width, new_height))
        except (pygame.error, FileNotFoundError) as e:
            logger.warning(f"Failed to load effect sprite {path}: {e}, using fallback")
            self.image = pygame.Surface((20, 20))
            self.image.fill(config.BLACK)
            
        self.rect = self.image.get_rect(center=self.position)

    def update(self):
        if self.effect_type == "EXPLOSION":
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.kill()
        elif self.is_moving:
            self.progress += self.speed
            if self.progress >= self.total_distance:
                if self.effect_type == "HIT":
                    # Create explosion on landing
                    # We pass the responsibility to GameApp to add it to its group
                    # For now, we'll keep the direct sprite group interaction as it was in the original code,
                    # but typically, sprite groups are managed by the main Game class.
                    # Since we don't have the group here, we'll just let the GameApp handle the visual trigger.
                    pass 
                
                self.kill()
            else:
                t = self.progress / self.total_distance
                self.position = self.start_pos + self.distance * t
                self.rect.center = (int(self.position.x), int(self.position.y))