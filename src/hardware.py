# src/hardware.py
import threading
import queue
import time
import os
import fcntl
import requests
import random 

# Conditional hardware imports
try:
# ... (hardware imports remain the same) ...
    import evdev
    from plasma import auto
    from evdev import InputDevice, ecodes
except ImportError:
# ... (placeholder imports remain the same) ...
    print("WARNING: Hardware libraries (evdev, plasma) not found. Using placeholder imports.")
    class InputDevice:
        def __init__(self, path): raise FileNotFoundError
        def fileno(self): return 0
        def read(self): yield None
    class auto:
        def __init__(self, **kwargs): pass
        def set_all(self, r, g, b, brightness=None): pass
        def set_pixel(self, i, r, g, b, brightness=None): pass
        def show(self): pass
    class ecodes:
        KEY_1 = 1; KEY_2 = 2; KEY_3 = 3; KEY_4 = 4; KEY_5 = 5
        KEY_6 = 6; KEY_7 = 7; KEY_8 = 8; KEY_9 = 9
        EV_KEY = 1
        

# Internal imports
from . import config
from . import battle_logic

# --- GLOBAL THREAD-SAFE QUEUE ---
event_queue = queue.Queue()

def trigger_ansible_job(final_score):
    """
    Sends an API request to Ansible Automation Platform (AWX/Tower).
    Moved from GameApp into the Hardware/Utility layer.
    """
# ... (trigger_ansible_job function remains the same) ...
    url = config.AAP_API_URL
    headers = {
        "Authorization": f"Bearer {config.AAP_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    
    data = {
        "extra_vars": {
            "game_score": int(final_score)
        }
    }

    print(f"AUTOMATION: Attempting to trigger Ansible job with score: {int(final_score)}")
    try:
        # Use verify=False if you have a self-signed certificate, otherwise remove it.
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=5) 
        response.raise_for_status() 
        
        if response.status_code == 201:
            print(f"AUTOMATION: Successfully triggered Ansible Job ID: {response.json().get('job', 'N/A')}")
        else:
            print(f"AUTOMATION: Job launch returned unexpected status code: {response.status_code}")
            
    except requests.exceptions.HTTPError as err:
        print(f"AUTOMATION ERROR: HTTP error occurred: {err}")
    except requests.exceptions.RequestException as err:
        print(f"AUTOMATION ERROR: Failed to connect to Ansible API: {err}")


class HardwareThread(threading.Thread):
    def __init__(self):
# ... (HardwareThread.__init__ remains the same) ...
        super().__init__()
        self.running = True
        self.is_available = False
        
        # Hardware setup
        try:
            # Use configuration constants
            self.plasma = auto(default=f"GPIO:14:15:pixel_count={config.NUM_PIXELS}")
            self.plasma.set_all(0, 0, 0)
            self.plasma.show()
            self.dev = InputDevice(config.device_path)
            
            # Set to non-blocking mode
            fd = self.dev.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            print(f"HARDWARE: Initialized and listening on {config.device_path}...")
            self.is_available = True
        except FileNotFoundError:
            print(f"HARDWARE: Error: Device not found at {config.device_path}. Running in simulation mode.")
        except Exception as e:
            print(f"HARDWARE: An error occurred during device setup: {e}. Running in simulation mode.")
        
        self.score = 0
        self.active_mole_light_index = None
        self.last_mole_time = 0
        self.game_start_time = 0
        
    def get_pixel_indices_for_light(self, light_index):
# ... (get_pixel_indices_for_light remains the same) ...
        start = light_index * config.PIXELS_PER_BUTTON
        end = start + config.PIXELS_PER_BUTTON
        return start, end

    def light_up_mole(self, light_index):
# ... (light_up_mole remains the same) ...
        if self.is_available:
            start_pixel, end_pixel = self.get_pixel_indices_for_light(light_index)
            for i in range(start_pixel, end_pixel):
                # Use config MOLE_COLOR
                self.plasma.set_pixel(i, config.MOLE_COLOR[0], config.MOLE_COLOR[1], config.MOLE_COLOR[2], brightness=0.25)
            self.plasma.show()

    def turn_off_mole(self, light_index):
# ... (turn_off_mole remains the same) ...
        if self.is_available and light_index is not None:
            start_pixel, end_pixel = self.get_pixel_indices_for_light(light_index)
            for i in range(start_pixel, end_pixel):
                self.plasma.set_pixel(i, 0, 0, 0, brightness=0.25)
            self.plasma.show()

    def light_up_all_red(self):
# ... (light_up_all_red remains the same) ...
        if self.is_available:
            self.plasma.set_all(255, 0, 0, brightness=0.25)
            self.plasma.show()
            time.sleep(config.PENALTY_FLASH_DURATION)
            self.plasma.set_all(0, 0, 0, brightness=0.25)
            self.plasma.show()

    def countdown_sequence(self):
        # Signal countdown start
        event_queue.put({"type": "COUNTDOWN_START"})
        
        if self.is_available:
            self.plasma.set_all(0, 0, 255, brightness=0.25) 
            self.plasma.show()
            time.sleep(config.COUNTDOWN_FLASH_DURATION * 2)
            self.plasma.set_all(0, 0, 0, brightness=0.25)
            time.sleep(config.COUNTDOWN_FLASH_DURATION)

            for i in range(3, 0, -1):
                self.light_up_mole(i - 1)
                time.sleep(config.COUNTDOWN_FLASH_DURATION)
                self.turn_off_mole(i - 1)
                time.sleep(config.COUNTDOWN_FLASH_DURATION)
        
        event_queue.put({"type": "COUNTDOWN_FINISHED"})

    def spawn_next_mole(self):
# ... (spawn_next_mole remains the same) ...
        """Helper to spawn the next mole immediately after a hit/miss."""
        self.turn_off_mole(self.active_mole_light_index)
        
        new_mole_index = random.randint(0, config.NUM_LIGHTS - 1)
        self.active_mole_light_index = new_mole_index
        self.light_up_mole(self.active_mole_light_index)
        self.last_mole_time = time.time()
        event_queue.put({"type": "MOLE_SPAWN", "index": new_mole_index})


    def run(self):
        while self.running:
            # Game Setup/Reset: Use the thread-safe reset function
            battle_logic.reset_game_for_new_round() 
            self.score = 0
            self.active_mole_light_index = None
            
            # --- START SCREEN ---
            event_queue.put({"type": "START_SCREEN"})
            
            self.turn_off_mole(self.active_mole_light_index)
            # Use KEY_TO_LIGHT_INDEX from config
            self.light_up_mole(config.KEY_TO_LIGHT_INDEX[ecodes.KEY_5])

            # Wait for '5' button press to start
            start_pressed = False
            while not start_pressed and self.running:
                try:
                    for event in self.dev.read():
                        if event.type == ecodes.EV_KEY and event.value == 1 and event.code == ecodes.KEY_5:
                            start_pressed = True
                            break
                except (IOError, BlockingIOError, AttributeError):
                    # FIX: Use minimal sleep instead of pass to avoid CPU hogging while waiting for input
                    time.sleep(0.001)

            if not self.running: break

            self.countdown_sequence()

            self.game_start_time = time.time()
            
            # Force the first mole spawn immediately after the game starts
            self.spawn_next_mole()

            # --- INNER GAME LOOP ---
            while self.running:
                current_time = time.time()
                time_elapsed = current_time - self.game_start_time
                
                # Check for Game End Condition (Time's Up OR Visual Layer Win/Loss)
                if time_elapsed >= config.GAME_DURATION or battle_logic.PLAYER_FORTRESS['health'] <= 0 or battle_logic.get_current_target_ship() is None:
                    break 

                # 1. Mole timer/spawning logic
                if (current_time - self.last_mole_time) > config.MOLE_DURATION:
                    if self.active_mole_light_index is not None:
                        event_queue.put({"type": "MOLE_ESCAPED"})
                        
                    self.spawn_next_mole()

                # 2. Read input
                if self.is_available:
                    try:
                        for event in self.dev.read():
                            if event.type == ecodes.EV_KEY and event.value == 1:
                                if self.active_mole_light_index is not None and event.code in config.KEY_TO_LIGHT_INDEX:
                                    pressed_light_index = config.KEY_TO_LIGHT_INDEX[event.code]

                                    if pressed_light_index == self.active_mole_light_index:
                                        self.score += 1
                                        event_queue.put({"type": "PLAYER_HIT", "score": self.score})
                                        
                                        self.spawn_next_mole() 
                                        
                                    else:
                                        self.score = max(0, self.score - 0.5)
                                        self.light_up_all_red()
                                        event_queue.put({"type": "PLAYER_MISS", "score": self.score})
                                        
                                        self.spawn_next_mole() 

                    except (IOError, BlockingIOError, AttributeError):
                        # FIX: Use minimal sleep instead of pass to reduce input read latency
                        time.sleep(0.001)
                
                # FIX: Replace the ambiguous 'pass' with a controlled sleep to maintain thread responsiveness
                time.sleep(0.001)

            # --- GAME OVER CLEANUP ---
            self.turn_off_mole(self.active_mole_light_index)
            if self.is_available:
                self.plasma.set_all(255, 255, 255, brightness=0.25)
                self.plasma.show()
                
            event_queue.put({"type": "GAME_OVER", "score": self.score})
            
            # NEW: Trigger Ansible job when the game ends
            trigger_ansible_job(self.score)

            # Wait for user input to restart
            keys_needed = 2
            keys_pressed = 0
            
            while keys_pressed < keys_needed and self.running:
                try:
                    for event in self.dev.read():
                        if event.type == ecodes.EV_KEY and event.value == 1:
                            keys_pressed += 1
                            print(f"HARDWARE: Key press detected. {keys_pressed}/{keys_needed} to continue.")
                            break 
                except (IOError, BlockingIOError, AttributeError):
                    time.sleep(0.05) 

            if not self.running: break
            
            if self.is_available:
                self.plasma.set_all(0, 0, 0, brightness=0.25)
                self.plasma.show()

    def stop(self):
        self.running = False
        if self.is_available:
            self.plasma.set_all(0, 0, 0)
            self.plasma.show()
        print("HARDWARE: Thread gracefully stopped.")