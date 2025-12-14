# src/exceptions.py
class GameError(Exception):
    """Base exception for all game-related errors."""
    pass

class HardwareError(GameError):
    """Hardware-related errors."""
    pass

class AssetError(GameError):
    """Asset loading errors."""
    pass

class ConfigError(GameError):
    """Configuration validation errors."""
    pass

class APIError(GameError):
    """External API communication errors."""
    pass