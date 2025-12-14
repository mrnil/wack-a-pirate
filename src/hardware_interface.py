# src/hardware_interface.py
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from .logger import setup_logger
from .exceptions import HardwareError

class HardwareInterface(ABC):
    """Abstract interface for hardware operations."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize hardware. Returns True if successful."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up hardware resources."""
        pass
    
    @abstractmethod
    def set_light(self, light_index: int, r: int, g: int, b: int, brightness: float = 0.25) -> None:
        """Set a specific light color."""
        pass
    
    @abstractmethod
    def set_all_lights(self, r: int, g: int, b: int, brightness: float = 0.25) -> None:
        """Set all lights to the same color."""
        pass
    
    @abstractmethod
    def show_lights(self) -> None:
        """Apply light changes."""
        pass
    
    @abstractmethod
    def read_input_events(self) -> List[Tuple[int, int]]:
        """Read input events. Returns list of (key_code, value) tuples."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if hardware is available."""
        pass
    
    @abstractmethod
    def get_health_status(self) -> dict:
        """Get hardware health information."""
        pass

class RaspberryPiHardware(HardwareInterface):
    """Real hardware implementation for Raspberry Pi."""
    
    def __init__(self, device_path: str, num_pixels: int):
        self.logger = setup_logger()
        self.device_path = device_path
        self.num_pixels = num_pixels
        self.plasma = None
        self.input_device = None
        self._available = False
        
    def initialize(self) -> bool:
        """Initialize Raspberry Pi hardware."""
        try:
            # Import hardware libraries
            from plasma import auto
            from evdev import InputDevice
            import fcntl
            import os
            
            # Initialize LED hardware
            self.plasma = auto(default=f"GPIO:14:15:pixel_count={self.num_pixels}")
            self.plasma.set_all(0, 0, 0)
            self.plasma.show()
            
            # Initialize input device
            self.input_device = InputDevice(self.device_path)
            
            # Set to non-blocking mode
            fd = self.input_device.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            self._available = True
            self.logger.info(f"Raspberry Pi hardware initialized: {self.device_path}")
            return True
            
        except ImportError as e:
            self.logger.error(f"Hardware libraries not available: {e}")
            raise HardwareError(f"Missing hardware libraries: {e}")
        except FileNotFoundError as e:
            self.logger.error(f"Input device not found: {self.device_path}")
            raise HardwareError(f"Input device not found: {e}")
        except PermissionError as e:
            self.logger.error(f"Permission denied accessing hardware: {e}")
            raise HardwareError(f"Hardware permission denied: {e}")
        except Exception as e:
            self.logger.error(f"Hardware initialization failed: {e}")
            raise HardwareError(f"Hardware setup failed: {e}")
    
    def cleanup(self) -> None:
        """Clean up hardware resources."""
        try:
            if self.plasma:
                self.plasma.set_all(0, 0, 0)
                self.plasma.show()
            self.logger.info("Hardware cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during hardware cleanup: {e}")
    
    def set_light(self, light_index: int, r: int, g: int, b: int, brightness: float = 0.25) -> None:
        """Set a specific light color."""
        if self.plasma and self._available:
            from . import config
            start_pixel = light_index * config.PIXELS_PER_BUTTON
            end_pixel = start_pixel + config.PIXELS_PER_BUTTON
            for i in range(start_pixel, end_pixel):
                self.plasma.set_pixel(i, r, g, b, brightness=brightness)
    
    def set_all_lights(self, r: int, g: int, b: int, brightness: float = 0.25) -> None:
        """Set all lights to the same color."""
        if self.plasma and self._available:
            self.plasma.set_all(r, g, b, brightness=brightness)
    
    def show_lights(self) -> None:
        """Apply light changes."""
        if self.plasma and self._available:
            self.plasma.show()
    
    def read_input_events(self) -> List[Tuple[int, int]]:
        """Read input events."""
        events = []
        if self.input_device and self._available:
            try:
                from evdev import ecodes
                for event in self.input_device.read():
                    if event.type == ecodes.EV_KEY:
                        events.append((event.code, event.value))
            except (IOError, BlockingIOError):
                pass  # No events available
        return events
    
    def is_available(self) -> bool:
        """Check if hardware is available."""
        return self._available
    
    def get_health_status(self) -> dict:
        """Get hardware health information."""
        return {
            "available": self._available,
            "device_path": self.device_path,
            "num_pixels": self.num_pixels,
            "plasma_initialized": self.plasma is not None,
            "input_initialized": self.input_device is not None
        }

class MockHardware(HardwareInterface):
    """Mock hardware implementation for testing and development."""
    
    def __init__(self):
        self.logger = setup_logger()
        self._available = True
        self.light_states = {}
        self.mock_events = []
        
    def initialize(self) -> bool:
        """Initialize mock hardware."""
        self.logger.info("Mock hardware initialized")
        return True
    
    def cleanup(self) -> None:
        """Clean up mock hardware."""
        self.light_states.clear()
        self.logger.info("Mock hardware cleanup complete")
    
    def set_light(self, light_index: int, r: int, g: int, b: int, brightness: float = 0.25) -> None:
        """Set a specific light color."""
        self.light_states[light_index] = (r, g, b, brightness)
        self.logger.debug(f"Mock light {light_index}: RGB({r},{g},{b}) brightness={brightness}")
    
    def set_all_lights(self, r: int, g: int, b: int, brightness: float = 0.25) -> None:
        """Set all lights to the same color."""
        from . import config
        for i in range(config.NUM_LIGHTS):
            self.light_states[i] = (r, g, b, brightness)
        self.logger.debug(f"Mock all lights: RGB({r},{g},{b}) brightness={brightness}")
    
    def show_lights(self) -> None:
        """Apply light changes."""
        pass  # Mock implementation - no actual display
    
    def read_input_events(self) -> List[Tuple[int, int]]:
        """Read mock input events."""
        events = self.mock_events.copy()
        self.mock_events.clear()
        return events
    
    def is_available(self) -> bool:
        """Check if hardware is available."""
        return self._available
    
    def inject_event(self, key_code: int, value: int) -> None:
        """Inject a mock input event for testing."""
        self.mock_events.append((key_code, value))
        self.logger.debug(f"Mock event injected: key={key_code}, value={value}")
    
    def get_health_status(self) -> dict:
        """Get hardware health information."""
        return {
            "available": self._available,
            "type": "mock",
            "lights_count": len(self.light_states),
            "pending_events": len(self.mock_events)
        }

def create_hardware(device_path: str, num_pixels: int, use_mock: bool = False) -> HardwareInterface:
    """Factory function to create appropriate hardware implementation."""
    if use_mock:
        return MockHardware()
    else:
        return RaspberryPiHardware(device_path, num_pixels)