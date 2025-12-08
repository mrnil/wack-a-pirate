# src/config.py
import os
from evdev import ecodes

# --- PATHS ---
ASSET_PATH = "kenney_pirate-pack (1)/PNG/Retina"
PIRATE_FONT_PATH = os.path.join("Pirata_One", "PirataOne-Regular.ttf")
device_path = '/dev/input/event0' # Raspberry Pi input device

# --- NEW PATH RESOLUTION HELPERS (START) ---
def _get_project_root():
    """Returns the absolute path to the parent directory (wack-a-pirate/)."""
    # os.path.dirname(__file__) is '.../src'
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def _resolve_path(path_constant):
    """Internal helper to safely resolve a path from a constant defined above.
       (path_constant is assumed to be relative to the assets/ folder)."""
    # This explicitly joins the Project Root, 'assets', and the path constant.
    return os.path.join(_get_project_root(), "assets", path_constant)

def resolve_asset_path(subpath):
    """Returns the absolute path for an asset inside the main asset folder (Retina)."""
    # Joins the resolved ASSET_PATH root with the specific subpath (e.g., 'Ships/ship (2).png')
    # ASSET_PATH is the sub-path "kenney_pirate-pack (1)/PNG/Retina"
    return os.path.join(_resolve_path(ASSET_PATH), subpath)

def resolve_font_path():
    """Returns the absolute path for the main font file."""
    # PIRATE_FONT_PATH is relative to the assets root
    return _resolve_path(PIRATE_FONT_PATH)
# --- NEW PATH RESOLUTION HELPERS (END) ---

# --- SCREEN & TIMING ---
# These are initial values, they will be updated by GameApp for fullscreen resolution
INITIAL_SCREEN_WIDTH = 800
INITIAL_SCREEN_HEIGHT = 600 
CAPTION = "Whack-A-Pirate Battle"
FPS = 200
GAME_DURATION = 30.0  # seconds
MOLE_DURATION = 0.75  # seconds
PENALTY_FLASH_DURATION = 0.2
COUNTDOWN_FLASH_DURATION = 0.5

# --- COLORS (RGB) ---
BLUE = (30, 144, 255) 
GREEN = (0, 200, 0)
RED = (200, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
MOLE_COLOR = (0, 255, 0)

# --- GAME & POSITIONING ---
SHIP_SPAWN_PADDING = 80 
PLAYER_MAX_HEALTH = 10

# --- HARDWARE/LIGHTS ---
NUM_LIGHTS = 9
PIXELS_PER_BUTTON = 4
NUM_PIXELS = NUM_LIGHTS * PIXELS_PER_BUTTON

KEY_TO_LIGHT_INDEX = {
    ecodes.KEY_1: 0, ecodes.KEY_2: 1, ecodes.KEY_3: 2, ecodes.KEY_4: 3,
    ecodes.KEY_5: 4, ecodes.KEY_6: 5, ecodes.KEY_7: 6, ecodes.KEY_8: 7,
    ecodes.KEY_9: 8,
}

# --- ANSIBLE AUTOMATION PLATFORM (AWX/Tower) API Configuration ---
# !!! IMPORTANT: REPLACE THESE PLACEHOLDER VALUES WITH YOUR ACTUAL DETAILS !!!
AAP_API_URL = "https://your-awx-server.com/api/v2/job_templates/123/launch/" 
AAP_AUTH_TOKEN = "YourAWXAutomationTokenHere" # Use an Authorization Bearer token

# --- SHIP CONFIGURATION DATA ---
SHIP_DATA = [
    # (Name, Max_HP, {"full": Path, "half": Path, "destroyed": Path})
    ("Sloop", 5, 
        {"full": "Ships/ship (5).png", "half": "Ships/ship (17).png", "destroyed": "Ships/ship (23).png"}),
    ("Brigantine", 10, 
        {"full": "Ships/ship (4).png", "half": "Ships/ship (16).png", "destroyed": "Ships/ship (22).png"}),
    ("Frigate", 15, 
        {"full": "Ships/ship (3).png", "half": "Ships/ship (15).png", "destroyed": "Ships/ship (23).png"}),
    ("Man-of-War", 15, 
        {"full": "Ships/ship (1).png", "half": "Ships/ship (13).png", "destroyed": "Ships/ship (19).png"}),
    ("Dreadnought (Boss)", 5, 
        {"full": "Ships/ship (6).png", "half": "Ships/ship (18).png", "destroyed": "Ships/ship (24).png"}),
]