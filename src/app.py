# src/app.py
import pygame
import sys
import os
import queue

# Internal imports
from . import config
from . import battle_logic
from . import hardware
from .sprites import EnemyShip, Cannon, Effect
from .game_states import GameStateMachine
from .logger import setup_logger
from .exceptions import GameError, AssetError, HardwareError

class GameApp:
    """The main class managing the Pygame lifecycle and rendering."""
    
    def __init__(self):
        self.logger = setup_logger()
        
        try:
            pygame.init()
            self._setup_screen()
            
            # Update shared dimensions after screen setup
            battle_logic.update_dimensions(self.screen.get_width(), self.screen.get_height())
            
            self.clock = pygame.time.Clock() 
            self.running = True
            self.last_game_score = 0
            self.prerendered_background = None
            
            # Initialize state machine
            self.state_machine = GameStateMachine(self)
            
            # Load resources with error handling
            self._load_resources()
            self._prerender_background() 
            
            # Initialize Game State
            battle_logic.initialize_fleet_structure()
            
            # Pygame Groups
            self.all_sprites = pygame.sprite.Group()
            self.cannon_sprites = pygame.sprite.Group()
            
            self.player_cannon = Cannon()
            self.cannon_sprites.add(self.player_cannon)

            # Hardware Thread with error handling
            try:
                self.hardware_thread = hardware.HardwareThread()
                self.hardware_thread.start()
                self.logger.info("Hardware thread started successfully")
            except Exception as e:
                self.logger.warning(f"Hardware initialization failed: {e}")
                raise HardwareError(f"Failed to initialize hardware: {e}")
                
        except pygame.error as e:
            self.logger.error(f"Pygame initialization failed: {e}")
            raise GameError(f"Failed to initialize game: {e}")
        except Exception as e:
            self.logger.error(f"Game initialization failed: {e}")
            raise

    def _setup_screen(self):
        """Initialize Pygame screen, defaulting to fullscreen if possible."""
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.logger.info("Fullscreen mode initialized")
        except pygame.error as e:
            self.logger.warning(f"Fullscreen failed: {e}, using windowed mode")
            try:
                self.screen = pygame.display.set_mode((config.INITIAL_SCREEN_WIDTH, config.INITIAL_SCREEN_HEIGHT))
                self.logger.info(f"Windowed mode initialized: {config.INITIAL_SCREEN_WIDTH}x{config.INITIAL_SCREEN_HEIGHT}")
            except pygame.error as e:
                raise GameError(f"Failed to initialize display: {e}")
            
        pygame.display.set_caption(config.CAPTION)

    def _load_resources(self):
        """Loads static assets like fonts and the ocean tile."""
        # Ocean Tile
        try:
            tile_path = config.resolve_asset_path("Tiles/tile_73.png")
            self.ocean_tile = pygame.image.load(tile_path).convert()
            self.logger.info("Ocean tile loaded successfully")
        except (pygame.error, FileNotFoundError) as e:
            self.logger.warning(f"Failed to load ocean tile: {e}, using solid color")
            self.ocean_tile = None
        
        # Fonts
        try:
            font_path = config.resolve_font_path()
            self.font_score = pygame.font.Font(font_path, 48)
            self.font_large = pygame.font.Font(font_path, 96)
            self.font_medium = pygame.font.Font(font_path, 64)
            self.font_small = pygame.font.Font(font_path, 48)
            self.logger.info("Custom fonts loaded successfully")
        except (pygame.error, FileNotFoundError) as e:
            self.logger.warning(f"Failed to load custom font: {e}, using default fonts")
            self.font_score = pygame.font.Font(None, 36)
            self.font_large = pygame.font.Font(None, 74)
            self.font_medium = pygame.font.Font(None, 48)
            self.font_small = pygame.font.Font(None, 36)

    def _prerender_background(self):
        """Creates a single large surface of the tiled ocean background for efficient blitting."""
        if self.ocean_tile is None:
            self.prerendered_background = None
            return

        try:
            screen_width = self.screen.get_width()
            screen_height = self.screen.get_height()
            tile_width = self.ocean_tile.get_width()
            tile_height = self.ocean_tile.get_height()
            
            self.prerendered_background = pygame.Surface((screen_width, screen_height)).convert()
            
            for x in range(0, screen_width, tile_width):
                for y in range(0, screen_height, tile_height):
                    self.prerendered_background.blit(self.ocean_tile, (x, y))
                    
            self.logger.info("Background prerendered successfully")
        except pygame.error as e:
            self.logger.error(f"Failed to prerender background: {e}")
            self.prerendered_background = None

    def _process_input(self):
        """Processes Pygame events (QUIT). Hardware input is handled by the thread."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def _process_hardware_events(self):
        """Reads events from the hardware thread queue and applies game mechanics."""
        while not hardware.event_queue.empty():
            try:
                event = hardware.event_queue.get_nowait()
                
                # Handle game mechanics
                if event['type'] == "START_SCREEN":
                    self.all_sprites.empty()
                    self.last_game_score = 0
                    
                elif event['type'] == "PLAYER_HIT" and self.state_machine.is_playing():
                    current_ship = battle_logic.get_current_target_ship()
                    if current_ship:
                        current_ship.take_damage() 
                        battle_logic.PLAYER_FORTRESS['health'] = min(
                            battle_logic.PLAYER_FORTRESS['health'] + 0.5, 
                            battle_logic.PLAYER_FORTRESS['max_health']
                        )
                        
                        cannonball = Effect(
                            self.player_cannon.rect.center, 
                            current_ship.rect.center,
                            "HIT"
                        )
                        self.all_sprites.add(cannonball)
                        
                elif event['type'] in ["PLAYER_MISS", "MOLE_ESCAPED"] and self.state_machine.is_playing():
                    current_ship = battle_logic.get_current_target_ship()
                    if current_ship and battle_logic.PLAYER_FORTRESS['health'] > 0:
                        battle_logic.PLAYER_FORTRESS['health'] = max(0, battle_logic.PLAYER_FORTRESS['health'] - 1) 
                        
                        cannonball = Effect(
                            current_ship.rect.center, 
                            self.player_cannon.rect.center,
                            "MISS"
                        )
                        self.all_sprites.add(cannonball)
                
                # Let state machine handle state transitions
                self.state_machine.handle_event(event)
                    
            except queue.Empty:
                break

    def _update(self):
        """Updates the state of all game objects."""
        self.all_sprites.update()
        self.cannon_sprites.update()
        self.state_machine.update()
        
    def _draw(self):
        """Renders the game state to the screen."""
        screen = self.screen
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        
        # 1. Draw Background (Optimized: single blit of the pre-rendered surface)
        if self.prerendered_background:
            screen.blit(self.prerendered_background, (0, 0))
        else:
            # Fallback if tile failed to load
            screen.fill(config.BLUE)

        # 2. Draw Ships (only during gameplay)
        if self.state_machine.is_playing():
            for ship in battle_logic.ENEMY_FLEET:
                if ship.battle_pos is not None and not ship.is_destroyed:
                    ship.rect.center = ship.battle_pos
                    ship.image = ship.get_current_sprite()
                    screen.blit(ship.image, ship.rect)
                    
                    # Draw Health Bar for current target
                    if ship == battle_logic.get_current_target_ship():
                        self._draw_ship_health(screen, ship)

        # 3. Draw Player Cannon and Health Bar (only during gameplay)
        if self.state_machine.is_playing():
            self.cannon_sprites.draw(screen)
            self.player_cannon.draw_health_bar(screen, self.font_small)
        
        # 4. Draw Effects (Cannonballs, Explosions)
        self.all_sprites.draw(screen)

        # 5. Draw UI (State-specific UI)
        self.state_machine.draw(screen)

        # 6. Final Flip
        pygame.display.flip()

    def _draw_ship_health(self, screen, ship):
        """Draws the health bar for the current target ship (helper function)."""
        BAR_WIDTH = ship.image.get_width()
        BAR_HEIGHT = 10
        
        x = ship.rect.left
        y = ship.rect.top - BAR_HEIGHT - 5 
        
        fill = (ship.current_health / ship.max_health) * BAR_WIDTH
        
        background_rect = pygame.Rect(x, y, BAR_WIDTH, BAR_HEIGHT)
        pygame.draw.rect(screen, config.RED, background_rect) 
        
        fill_rect = pygame.Rect(x, y, fill, BAR_HEIGHT)
        pygame.draw.rect(screen, config.GREEN, fill_rect) 
        
        pygame.draw.rect(screen, config.BLACK, background_rect, 1)


            
    def shutdown(self):
        """Gracefully stops threads and quits Pygame."""
        self.logger.info("Shutting down game")
        try:
            if hasattr(self, 'hardware_thread'):
                self.hardware_thread.stop()
                self.hardware_thread.join(timeout=5.0)
                if self.hardware_thread.is_alive():
                    self.logger.warning("Hardware thread did not stop gracefully")
        except Exception as e:
            self.logger.error(f"Error stopping hardware thread: {e}")
        
        try:
            pygame.quit()
            self.logger.info("Pygame shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during Pygame shutdown: {e}")

    def run(self):
        """The main game loop."""
        try:
            while self.running:
                # 1. Frame rate limiting
                self.clock.tick(config.FPS)
                
                # 2. Handle Pygame input
                self._process_input()
                
                # 3. Handle external (hardware) events
                self._process_hardware_events()
                
                # 4. Update game state
                self._update()
                
                # 5. Draw to screen
                self._draw()
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt detected")
            self.running = False
        except Exception as e:
            self.logger.error(f"Unexpected error in game loop: {e}", exc_info=True)
            self.running = False
        finally:
            self.shutdown()