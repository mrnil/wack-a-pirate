# src/hardware.py
import threading
import queue
import time
import os
import fcntl
import requests
import random 

# Hardware abstraction
from .hardware_interface import create_hardware, HardwareInterface

# Import ecodes with fallback
try:
    from evdev import ecodes
except ImportError:
    class ecodes:
        KEY_1 = 1; KEY_2 = 2; KEY_3 = 3; KEY_4 = 4; KEY_5 = 5
        KEY_6 = 6; KEY_7 = 7; KEY_8 = 8; KEY_9 = 9
        EV_KEY = 1
        

# Internal imports
from . import config
from . import battle_logic
from .logger import setup_logger
from .exceptions import HardwareError, APIError
from .events import (
    event_dispatcher, StartScreenEvent, CountdownStartEvent, CountdownFinishedEvent,
    PlayerHitEvent, PlayerMissEvent, MoleEscapedEvent, MoleSpawnEvent, GameOverEvent
)

# Legacy queue for backward compatibility during transition
event_queue = queue.Queue()

def trigger_ansible_job(final_score, max_retries=3):
    """
    Sends an API request to Ansible Automation Platform with retry logic.
    """
    logger = setup_logger()
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

    logger.info(f"Triggering Ansible job with score: {int(final_score)}")
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, verify=False, timeout=10)
            response.raise_for_status()
            
            if response.status_code == 201:
                job_id = response.json().get('job', 'N/A')
                logger.info(f"Successfully triggered Ansible Job ID: {job_id}")
                return
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"Ansible API timeout (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    logger.error("Failed to trigger Ansible job after all retries")
    raise APIError("Failed to trigger Ansible automation after retries")


class HardwareThread(threading.Thread):
    def __init__(self, use_mock_hardware: bool = False):
        super().__init__()
        self.logger = setup_logger()
        self.running = True
        self.use_mock_hardware = use_mock_hardware
        
        # Initialize hardware through abstraction layer
        try:
            self.hardware = create_hardware(
                config.device_path, 
                config.NUM_PIXELS, 
                use_mock=use_mock_hardware
            )
            self.hardware.initialize()
            self.logger.info(f"Hardware initialized (mock={use_mock_hardware})")
            
        except HardwareError as e:
            self.logger.error(f"Hardware initialization failed: {e}")
            # Fall back to mock hardware
            self.logger.info("Falling back to mock hardware")
            self.hardware = create_hardware(config.device_path, config.NUM_PIXELS, use_mock=True)
            self.hardware.initialize()
        
        self.score = 0
        self.active_mole_light_index = None
        self.last_mole_time = 0
        self.game_start_time = 0
        
    def light_up_mole(self, light_index):
        """Light up a specific mole."""
        if self.hardware.is_available():
            self.hardware.set_light(
                light_index, 
                config.MOLE_COLOR[0], 
                config.MOLE_COLOR[1], 
                config.MOLE_COLOR[2]
            )
            self.hardware.show_lights()

    def turn_off_mole(self, light_index):
        """Turn off a specific mole."""
        if self.hardware.is_available() and light_index is not None:
            self.hardware.set_light(light_index, 0, 0, 0)
            self.hardware.show_lights()

    def light_up_all_red(self):
        """Flash all lights red for penalty."""
        if self.hardware.is_available():
            self.hardware.set_all_lights(255, 0, 0)
            self.hardware.show_lights()
            time.sleep(config.PENALTY_FLASH_DURATION)
            self.hardware.set_all_lights(0, 0, 0)
            self.hardware.show_lights()

    def countdown_sequence(self):
        # Signal countdown start
        event_dispatcher.dispatch(CountdownStartEvent())
        
        if self.hardware.is_available():
            self.hardware.set_all_lights(0, 0, 255)
            self.hardware.show_lights()
            time.sleep(config.COUNTDOWN_FLASH_DURATION * 2)
            self.hardware.set_all_lights(0, 0, 0)
            self.hardware.show_lights()
            time.sleep(config.COUNTDOWN_FLASH_DURATION)

            for i in range(3, 0, -1):
                self.light_up_mole(i - 1)
                time.sleep(config.COUNTDOWN_FLASH_DURATION)
                self.turn_off_mole(i - 1)
                time.sleep(config.COUNTDOWN_FLASH_DURATION)
        
        event_dispatcher.dispatch(CountdownFinishedEvent())

    def spawn_next_mole(self):
        """Helper to spawn the next mole immediately after a hit/miss."""
        self.turn_off_mole(self.active_mole_light_index)
        
        new_mole_index = random.randint(0, config.NUM_LIGHTS - 1)
        self.active_mole_light_index = new_mole_index
        self.light_up_mole(self.active_mole_light_index)
        self.last_mole_time = time.time()
        event_dispatcher.dispatch(MoleSpawnEvent(light_index=new_mole_index))


    def run(self):
        while self.running:
            # Game Setup/Reset: Use the thread-safe reset function
            battle_logic.reset_game_for_new_round() 
            self.score = 0
            self.active_mole_light_index = None
            
            # --- START SCREEN ---
            event_dispatcher.dispatch(StartScreenEvent())
            
            self.turn_off_mole(self.active_mole_light_index)
            # Use KEY_TO_LIGHT_INDEX from config
            self.light_up_mole(config.KEY_TO_LIGHT_INDEX[ecodes.KEY_5])

            # Wait for '5' button press to start
            start_pressed = False
            while not start_pressed and self.running:
                try:
                    events = self.hardware.read_input_events()
                    for event_code, event_value in events:
                        if event_value == 1 and event_code == ecodes.KEY_5:
                            start_pressed = True
                            break
                except Exception as e:
                    self.logger.error(f"Error reading start input: {e}")
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
                        event_dispatcher.dispatch(MoleEscapedEvent())
                        
                    self.spawn_next_mole()

                # 2. Read input
                if self.hardware.is_available():
                    try:
                        events = self.hardware.read_input_events()
                        for event_code, event_value in events:
                            if event_value == 1:  # Key press
                                if self.active_mole_light_index is not None and event_code in config.KEY_TO_LIGHT_INDEX:
                                    pressed_light_index = config.KEY_TO_LIGHT_INDEX[event_code]

                                    if pressed_light_index == self.active_mole_light_index:
                                        self.score += 1
                                        event_dispatcher.dispatch(PlayerHitEvent(score=int(self.score)))
                                        
                                        self.spawn_next_mole() 
                                        
                                    else:
                                        self.score = max(0, self.score - 0.5)
                                        self.light_up_all_red()
                                        event_dispatcher.dispatch(PlayerMissEvent(score=self.score))
                                        
                                        self.spawn_next_mole()

                    except Exception as e:
                        self.logger.error(f"Error reading input events: {e}")
                        time.sleep(0.001)
                
                # FIX: Replace the ambiguous 'pass' with a controlled sleep to maintain thread responsiveness
                time.sleep(0.001)

            # --- GAME OVER CLEANUP ---
            self.turn_off_mole(self.active_mole_light_index)
            if self.hardware.is_available():
                self.hardware.set_all_lights(255, 255, 255)
                self.hardware.show_lights()
                
            # Determine game over reason
            if time_elapsed >= config.GAME_DURATION:
                reason = "time_up"
            elif battle_logic.PLAYER_FORTRESS['health'] <= 0:
                reason = "defeat"
            elif battle_logic.get_current_target_ship() is None:
                reason = "victory"
            else:
                reason = "unknown"
                
            event_dispatcher.dispatch(GameOverEvent(score=self.score, reason=reason))
            
            # Trigger Ansible job when the game ends
            try:
                trigger_ansible_job(self.score)
            except APIError as e:
                self.logger.error(f"Ansible automation failed: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in automation: {e}")

            # Wait for user input to restart
            keys_needed = 2
            keys_pressed = 0
            
            while keys_pressed < keys_needed and self.running:
                try:
                    events = self.hardware.read_input_events()
                    for event_code, event_value in events:
                        if event_value == 1:  # Key press
                            keys_pressed += 1
                            self.logger.info(f"Key press detected. {keys_pressed}/{keys_needed} to continue.")
                            break 
                except Exception as e:
                    self.logger.error(f"Error reading restart input: {e}")
                    time.sleep(0.05) 

            if not self.running: break
            
            if self.hardware.is_available():
                self.hardware.set_all_lights(0, 0, 0)
                self.hardware.show_lights()

    def stop(self):
        self.running = False
        try:
            if hasattr(self, 'hardware'):
                self.hardware.cleanup()
            self.logger.info("Hardware thread stopped gracefully")
        except Exception as e:
            self.logger.error(f"Error during hardware cleanup: {e}")