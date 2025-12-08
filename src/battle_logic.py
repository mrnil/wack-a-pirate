# src/battle_logic.py
import pygame
import random
import math
from . import config
from .sprites import EnemyShip

# --- GLOBAL GAME STATE (Managed by HardwareThread and read/drawn by GameApp) ---
ENEMY_FLEET = []
PLAYER_FORTRESS = {'health': config.PLAYER_MAX_HEALTH, 'max_health': config.PLAYER_MAX_HEALTH}
SCREEN_WIDTH = config.INITIAL_SCREEN_WIDTH
SCREEN_HEIGHT = config.INITIAL_SCREEN_HEIGHT
MIN_SHIP_DISTANCE = min(SCREEN_WIDTH, SCREEN_HEIGHT) // 3

def update_dimensions(width, height):
    """Called by GameApp after screen initialization."""
    global SCREEN_WIDTH, SCREEN_HEIGHT, MIN_SHIP_DISTANCE
    SCREEN_WIDTH = width
    SCREEN_HEIGHT = height
    MIN_SHIP_DISTANCE = min(SCREEN_WIDTH, SCREEN_HEIGHT) // 3

def initialize_fleet_structure():
    """
    Creates the ship objects and assigns fixed, non-overlapping positions.
    Images are loaded here and persist throughout the program run.
    """
    global ENEMY_FLEET
    
    # Must be called after update_dimensions
    if ENEMY_FLEET:
        return # Already initialized

    ENEMY_FLEET = [
        # Pass the sprite loading responsibility to the EnemyShip class
        EnemyShip(name, health, paths) for name, health, paths in config.SHIP_DATA
    ]
    
    placed_positions = []
    for ship in ENEMY_FLEET:
        # Check if dimensions are valid before calculating position
        if SCREEN_WIDTH > 0 and SCREEN_HEIGHT > 0:
            ship.battle_pos = generate_non_overlapping_position(
                ship.image.get_size(), 
                MIN_SHIP_DISTANCE, 
                placed_positions, 
                config.SHIP_SPAWN_PADDING
            )
            placed_positions.append(ship.battle_pos)

def reset_game_for_new_round():
    """
    Safely resets the state of existing objects without reloading any images.
    Called by the HardwareThread.
    """
    global ENEMY_FLEET, PLAYER_FORTRESS
    
    if not ENEMY_FLEET:
        # If fleet hasn't been initialized (e.g., failed asset loading), try to init
        initialize_fleet_structure() 
        if not ENEMY_FLEET:
             return

    for ship in ENEMY_FLEET:
        ship.current_health = ship.max_health
        ship.is_destroyed = False
        ship.image = ship.images["full"] # Reset visual state

    PLAYER_FORTRESS['health'] = PLAYER_FORTRESS['max_health']
    
def get_current_target_ship():
    """Returns the first ship in the fleet that is NOT yet destroyed."""
    for ship in ENEMY_FLEET:
        if not ship.is_destroyed:
            return ship
    return None

def generate_non_overlapping_position(ship_size, min_distance, existing_positions, padding):
    """
    Generates a random (x, y) coordinate that is far from the center and 
    does not overlap with existing_positions.
    """
    CENTER_X = SCREEN_WIDTH // 2
    CENTER_Y = SCREEN_HEIGHT // 2
    
    # Ensure there is room to spawn
    MAX_DISTANCE = min(CENTER_X, CENTER_Y) - 50 
    
    i = 0
    while i < 1000: 
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(min_distance, MAX_DISTANCE)

        x = CENTER_X + distance * math.cos(angle)
        y = CENTER_Y + distance * math.sin(angle)
        
        new_pos = pygame.Vector2(x, y)
        is_overlapping = False

        for existing_pos in existing_positions:
            dist_to_other = new_pos.distance_to(pygame.Vector2(existing_pos))
            # Rough distance check based on average size + padding
            if dist_to_other < (ship_size[0] + ship_size[1]) / 2 + padding:
                is_overlapping = True
                break
        
        # Check screen bounds
        if not is_overlapping and 50 < x < SCREEN_WIDTH - 50 and 50 < y < SCREEN_HEIGHT - 50:
            return (int(x), int(y))

        i += 1
    
    # Fallback position if placement fails
    return (SCREEN_WIDTH - 100, 100)