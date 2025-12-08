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

class GameApp:
    """The main class managing the Pygame lifecycle and rendering."""
    
    def __init__(self):
        pygame.init()
        
        self._setup_screen()
        
        # Update shared dimensions after screen setup
        battle_logic.update_dimensions(self.screen.get_width(), self.screen.get_height())
        
        self.clock = pygame.time.Clock() 
        self.running = True
        self.game_running = False
        self.game_over = False
        self.last_game_score = 0
        self.prerendered_background = None # Initialize new attribute
        
        # Load resources
        self._load_resources()
        
        # *** OPTIMIZATION STEP: Pre-render the tiled background once ***
        self._prerender_background() 
        
        # Initialize Game State
        battle_logic.initialize_fleet_structure()
        
        # Pygame Groups
        self.all_sprites = pygame.sprite.Group()
        self.cannon_sprites = pygame.sprite.Group()
        
        self.player_cannon = Cannon()
        self.cannon_sprites.add(self.player_cannon)

        # Hardware Thread
        self.hardware_thread = hardware.HardwareThread()
        self.hardware_thread.start()

    def _setup_screen(self):
        """Initialize Pygame screen, defaulting to fullscreen if possible."""
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            self.screen = pygame.display.set_mode((config.INITIAL_SCREEN_WIDTH, config.INITIAL_SCREEN_HEIGHT))
            
        pygame.display.set_caption(config.CAPTION)

    def _load_resources(self):
        """Loads static assets like fonts and the ocean tile."""
        # Ocean Tile
        try:
            # FIX: Use the robust path resolver for the tile image
            tile_path = config.resolve_asset_path("Tiles/tile_73.png")
            # IMPORTANT: Use convert() for non-transparent backgrounds
            self.ocean_tile = pygame.image.load(tile_path).convert()
        except pygame.error:
            print("Error loading tile_73.png. Using solid color.")
            self.ocean_tile = None
        
        # Fonts
        try:
            font_path = config.PIRATE_FONT_PATH
            self.font_score = pygame.font.Font(font_path, 48)
            self.font_large = pygame.font.Font(font_path, 96)
            self.font_medium = pygame.font.Font(font_path, 64)
            self.font_small = pygame.font.Font(font_path, 48)
        except Exception:
            self.font_score = pygame.font.Font(None, 36)
            self.font_large = pygame.font.Font(None, 74)
            self.font_medium = pygame.font.Font(None, 48)
            self.font_small = pygame.font.Font(None, 36)

    def _prerender_background(self):
        """Creates a single large surface of the tiled ocean background for efficient blitting.
        This runs only once at startup."""
        if self.ocean_tile is None:
            self.prerendered_background = None
            return

        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        tile_width = self.ocean_tile.get_width()
        tile_height = self.ocean_tile.get_height()
        
        # 1. Create a surface the size of the screen and use convert() for speed
        self.prerendered_background = pygame.Surface((screen_width, screen_height)).convert()
        
        # 2. Draw the ocean tile onto the new surface repeatedly (only once at init)
        for x in range(0, screen_width, tile_width):
            for y in range(0, screen_height, tile_height):
                self.prerendered_background.blit(self.ocean_tile, (x, y))

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
                
                if event['type'] == "START_SCREEN":
                    self.all_sprites.empty()
                    self.game_running = False
                    self.game_over = False
                    self.last_game_score = 0 
                    
                elif event['type'] == "COUNTDOWN_FINISHED":
                    self.game_running = True
                    
                elif event['type'] == "PLAYER_HIT":
                    current_ship = battle_logic.get_current_target_ship()
                    if current_ship:
                        # 1. MECHANICS: INSTANT DAMAGE AND HEAL
                        current_ship.take_damage() 
                        battle_logic.PLAYER_FORTRESS['health'] = min(
                            battle_logic.PLAYER_FORTRESS['health'] + 0.5, 
                            battle_logic.PLAYER_FORTRESS['max_health']
                        )
                        
                        # 2. VISUALS: CREATE CANNONBALL
                        cannonball = Effect(
                            self.player_cannon.rect.center, 
                            current_ship.rect.center,
                            "HIT"
                        )
                        self.all_sprites.add(cannonball)
                        
                elif event['type'] == "PLAYER_MISS" or event['type'] == "MOLE_ESCAPED":
                    current_ship = battle_logic.get_current_target_ship()
                    if current_ship and battle_logic.PLAYER_FORTRESS['health'] > 0:
                        # 1. MECHANICS: ENEMY INSTANT DAMAGE
                        battle_logic.PLAYER_FORTRESS['health'] = max(0, battle_logic.PLAYER_FORTRESS['health'] - 1) 
                        
                        # 2. VISUALS: CREATE RETURN CANNONBALL
                        cannonball = Effect(
                            current_ship.rect.center, 
                            self.player_cannon.rect.center,
                            "MISS"
                        )
                        self.all_sprites.add(cannonball)

                elif event['type'] == "GAME_OVER":
                    self.game_over = True
                    self.last_game_score = int(event.get('score', 0)) 
                    # Ansible trigger moved to HardwareThread
                    
            except queue.Empty:
                break
                
        # Check for Win/Loss state change caused by object updates (redundant check for safety)
        if self.game_running and (battle_logic.PLAYER_FORTRESS['health'] <= 0 or battle_logic.get_current_target_ship() is None):
            self.game_over = True

    def _update(self):
        """Updates the state of all game objects."""
        self.all_sprites.update()
        self.cannon_sprites.update()
        
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

        # 2. Draw Ships
        for ship in battle_logic.ENEMY_FLEET:
            if ship.battle_pos is not None and not ship.is_destroyed:
                ship.rect.center = ship.battle_pos
                ship.image = ship.get_current_sprite()
                screen.blit(ship.image, ship.rect)
                
                # Draw Health Bar for current target
                if ship == battle_logic.get_current_target_ship():
                    self._draw_ship_health(screen, ship)

        # 3. Draw Player Cannon and Health Bar
        self.cannon_sprites.draw(screen)
        self.player_cannon.draw_health_bar(screen, self.font_small)
        
        # 4. Draw Effects (Cannonballs, Explosions)
        self.all_sprites.draw(screen)

        # 5. Draw UI (Score, Game Over/Start Screen)
        self._draw_ui(screen, screen_width, screen_height)

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

    def _draw_ui(self, screen, screen_width, screen_height):
        """Handles drawing the score, start screen, and game over screens."""
        CENTER_X = screen_width // 2
        CENTER_Y = screen_height // 2
        
        if self.game_running and not self.game_over:
            # SCORING DISPLAY (TOP RIGHT)
            score_display_text = f"SCORE: {int(self.hardware_thread.score)}"
            score_surface = self.font_score.render(score_display_text, True, config.WHITE)
            score_rect = score_surface.get_rect(topright=(screen_width - 10, 10))
            
            TEXT_BOX_PADDING = 10 
            box_rect = score_rect.inflate(TEXT_BOX_PADDING * 2, TEXT_BOX_PADDING * 2)
            
            sheer_surface = pygame.Surface(box_rect.size, pygame.SRCALPHA)
            sheer_surface.fill((0, 0, 0, 150)) # Black with 150 alpha
            screen.blit(sheer_surface, box_rect.topleft)
            screen.blit(score_surface, score_rect)

        elif self.game_over:
            # GAME OVER SCREEN
            BOX_PADDING = 30
            if battle_logic.PLAYER_FORTRESS['health'] <= 0:
                message = "DEFEAT! FORTRESS DESTROYED!"
                color = config.RED
            elif battle_logic.get_current_target_ship() is None:
                message = "VICTORY! ALL SHIPS SUNK!"
                color = (255, 215, 0) # Gold
            else:
                message = "TIME'S UP!"
                color = config.WHITE
            
            score_text = f"FINAL SCORE: {self.last_game_score}"
            prompt_text = "PRESS ANY BUTTON TO CONTINUE"

            text_surface_large = self.font_large.render(message, True, color)
            text_surface_medium = self.font_medium.render(score_text, True, config.WHITE)
            text_surface_small = self.font_small.render(prompt_text, True, config.WHITE)

            # Calculate Bounding Box dimensions
            top_line_top = (CENTER_Y - 80) - (text_surface_large.get_height() / 2)
            bottom_line_bottom = (CENTER_Y + 90) + (text_surface_small.get_height() / 2)
            box_top_y = int(top_line_top - BOX_PADDING)
            box_height = int(bottom_line_bottom - top_line_top + 2 * BOX_PADDING)
            max_width = max(text_surface_large.get_width(), text_surface_medium.get_width(), text_surface_small.get_width())
            box_width = max_width + (2 * BOX_PADDING)
            box_left_x = CENTER_X - (box_width // 2)

            sheer_box_rect = pygame.Rect(box_left_x, box_top_y, box_width, box_height)
            sheer_surface = pygame.Surface(sheer_box_rect.size, pygame.SRCALPHA)
            sheer_surface.fill((0, 0, 0, 150)) 
            screen.blit(sheer_surface, sheer_box_rect.topleft)

            # Draw text lines
            screen.blit(text_surface_large, text_surface_large.get_rect(center=(CENTER_X, CENTER_Y - 80)))
            screen.blit(text_surface_medium, text_surface_medium.get_rect(center=(CENTER_X, CENTER_Y + 10)))
            screen.blit(text_surface_small, self.font_small.render(prompt_text, True, config.WHITE).get_rect(center=(CENTER_X, CENTER_Y + 90)))
            
        elif not self.game_running and not self.game_over:
            # START SCREEN
            text = "PRESS 5 TO START BATTLE"
            text_surface = self.font_medium.render(text, True, config.WHITE)
            text_rect = text_surface.get_rect(center=(CENTER_X, CENTER_Y))
            
            TEXT_BOX_PADDING = 15
            box_rect = text_rect.inflate(TEXT_BOX_PADDING * 2, TEXT_BOX_PADDING * 2)
            
            sheer_surface = pygame.Surface(box_rect.size, pygame.SRCALPHA)
            sheer_surface.fill((0, 0, 0, 150)) 
            screen.blit(sheer_surface, box_rect.topleft)
            screen.blit(text_surface, text_rect)
            
    def shutdown(self):
        """Gracefully stops threads and quits Pygame."""
        print("Cleaning up threads and Pygame resources.")
        self.hardware_thread.stop()
        self.hardware_thread.join()
        pygame.quit()

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
            print("\nKeyboard interrupt detected. Initiating graceful shutdown...")
            self.running = False
        finally:
            self.shutdown()
            sys.exit()