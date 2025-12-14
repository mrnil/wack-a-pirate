# src/events.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Type
from .logger import setup_logger

class GameEvent(ABC):
    """Base class for all game events."""
    pass

@dataclass
class StartScreenEvent(GameEvent):
    """Event triggered when returning to start screen."""
    pass

@dataclass
class CountdownStartEvent(GameEvent):
    """Event triggered when countdown begins."""
    pass

@dataclass
class CountdownFinishedEvent(GameEvent):
    """Event triggered when countdown completes."""
    pass

@dataclass
class PlayerHitEvent(GameEvent):
    """Event triggered when player hits correct target."""
    score: int

@dataclass
class PlayerMissEvent(GameEvent):
    """Event triggered when player hits wrong target."""
    score: float

@dataclass
class MoleEscapedEvent(GameEvent):
    """Event triggered when mole timer expires."""
    pass

@dataclass
class MoleSpawnEvent(GameEvent):
    """Event triggered when new mole spawns."""
    light_index: int

@dataclass
class GameOverEvent(GameEvent):
    """Event triggered when game ends."""
    score: float
    reason: str = "time_up"  # "time_up", "defeat", "victory"

@dataclass
class ShipDestroyedEvent(GameEvent):
    """Event triggered when a ship is destroyed."""
    ship_name: str

class EventDispatcher:
    """Centralized event dispatcher using observer pattern."""
    
    def __init__(self):
        self.logger = setup_logger()
        self._listeners: Dict[Type[GameEvent], List[Callable]] = {}
        
    def subscribe(self, event_type: Type[GameEvent], callback: Callable[[GameEvent], None]):
        """Subscribe to an event type."""
        if not issubclass(event_type, GameEvent):
            self.logger.error(f"Invalid event type for subscription: {event_type}")
            return
            
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        self.logger.debug(f"Subscribed to {event_type.__name__}")
        
    def unsubscribe(self, event_type: Type[GameEvent], callback: Callable[[GameEvent], None]):
        """Unsubscribe from an event type."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                self.logger.debug(f"Unsubscribed from {event_type.__name__}")
            except ValueError:
                self.logger.warning(f"Callback not found for {event_type.__name__}")
                
    def dispatch(self, event: GameEvent):
        """Dispatch an event to all subscribers."""
        if not isinstance(event, GameEvent):
            self.logger.error(f"Invalid event type: {type(event)}")
            return
            
        event_type = type(event)
        self.logger.debug(f"Dispatching {event_type.__name__}")
        
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error in event callback for {event_type.__name__}: {e}")
                    
    def clear_all(self):
        """Clear all event listeners."""
        self._listeners.clear()
        self.logger.info("All event listeners cleared")

# Global event dispatcher instance
event_dispatcher = EventDispatcher()