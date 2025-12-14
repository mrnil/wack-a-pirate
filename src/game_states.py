# src/game_states.py
from abc import ABC, abstractmethod
from enum import Enum
import pygame
from . import config

class GameStateType(Enum):
    START_SCREEN = "start_screen"
    COUNTDOWN = "countdown"
    PLAYING = "playing"
    GAME_OVER = "game_over"

class GameState(ABC):
    """Base class for all game states."""
    
    def __init__(self, app):
        self.app = app
        
    @abstractmethod
    def handle_event(self, event):
        """Handle hardware events specific to this state."""
        pass
        
    @abstractmethod
    def update(self):
        """Update state logic."""
        pass
        
    @abstractmethod
    def draw(self, screen):
        """Draw state-specific UI elements."""
        pass

class StartScreenState(GameState):
    """Initial state waiting for player to start the game."""
    
    def handle_event(self, event):
        if event.get('type') == "START_SCREEN":
            return GameStateType.START_SCREEN
        elif event.get('type') == "COUNTDOWN_START":
            return GameStateType.COUNTDOWN
        return None
        
    def update(self):
        pass
        
    def draw(self, screen):
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        text = "PRESS 5 TO START BATTLE"
        text_surface = self.app.font_medium.render(text, True, config.WHITE)
        text_rect = text_surface.get_rect(center=(center_x, center_y))
        
        padding = 15
        box_rect = text_rect.inflate(padding * 2, padding * 2)
        
        sheer_surface = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        sheer_surface.fill((0, 0, 0, 150))
        screen.blit(sheer_surface, box_rect.topleft)
        screen.blit(text_surface, text_rect)

class CountdownState(GameState):
    """Countdown before game starts."""
    
    def handle_event(self, event):
        if event.get('type') == "COUNTDOWN_FINISHED":
            return GameStateType.PLAYING
        return None
        
    def update(self):
        pass
        
    def draw(self, screen):
        # Countdown is handled by hardware thread, no UI needed
        pass

class PlayingState(GameState):
    """Active gameplay state."""
    
    def handle_event(self, event):
        if event.get('type') == "GAME_OVER":
            self.app.last_game_score = int(event.get('score', 0))
            return GameStateType.GAME_OVER
        return None
        
    def update(self):
        from . import battle_logic
        # Check win/loss conditions
        if (battle_logic.PLAYER_FORTRESS['health'] <= 0 or 
            battle_logic.get_current_target_ship() is None):
            return GameStateType.GAME_OVER
        return None
        
    def draw(self, screen):
        screen_width = screen.get_width()
        
        # Draw score
        score_text = f"SCORE: {int(self.app.hardware_thread.score)}"
        score_surface = self.app.font_score.render(score_text, True, config.WHITE)
        score_rect = score_surface.get_rect(topright=(screen_width - 10, 10))
        
        padding = 10
        box_rect = score_rect.inflate(padding * 2, padding * 2)
        
        sheer_surface = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        sheer_surface.fill((0, 0, 0, 150))
        screen.blit(sheer_surface, box_rect.topleft)
        screen.blit(score_surface, score_rect)

class GameOverState(GameState):
    """Game over screen showing results."""
    
    def handle_event(self, event):
        if event.get('type') == "START_SCREEN":
            return GameStateType.START_SCREEN
        return None
        
    def update(self):
        pass
        
    def draw(self, screen):
        from . import battle_logic
        
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Determine message and color
        if battle_logic.PLAYER_FORTRESS['health'] <= 0:
            message = "DEFEAT! FORTRESS DESTROYED!"
            color = config.RED
        elif battle_logic.get_current_target_ship() is None:
            message = "VICTORY! ALL SHIPS SUNK!"
            color = (255, 215, 0)  # Gold
        else:
            message = "TIME'S UP!"
            color = config.WHITE
        
        score_text = f"FINAL SCORE: {self.app.last_game_score}"
        prompt_text = "PRESS ANY BUTTON TO CONTINUE"
        
        # Render text
        text_large = self.app.font_large.render(message, True, color)
        text_medium = self.app.font_medium.render(score_text, True, config.WHITE)
        text_small = self.app.font_small.render(prompt_text, True, config.WHITE)
        
        # Calculate box dimensions
        padding = 30
        top_y = (center_y - 80) - (text_large.get_height() / 2)
        bottom_y = (center_y + 90) + (text_small.get_height() / 2)
        box_height = int(bottom_y - top_y + 2 * padding)
        max_width = max(text_large.get_width(), text_medium.get_width(), text_small.get_width())
        box_width = max_width + (2 * padding)
        box_x = center_x - (box_width // 2)
        
        # Draw background box
        box_rect = pygame.Rect(box_x, int(top_y - padding), box_width, box_height)
        sheer_surface = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        sheer_surface.fill((0, 0, 0, 150))
        screen.blit(sheer_surface, box_rect.topleft)
        
        # Draw text
        screen.blit(text_large, text_large.get_rect(center=(center_x, center_y - 80)))
        screen.blit(text_medium, text_medium.get_rect(center=(center_x, center_y + 10)))
        screen.blit(text_small, text_small.get_rect(center=(center_x, center_y + 90)))

class GameStateMachine:
    """Manages game state transitions."""
    
    def __init__(self, app):
        self.app = app
        self.current_state_type = GameStateType.START_SCREEN
        self.states = {
            GameStateType.START_SCREEN: StartScreenState(app),
            GameStateType.COUNTDOWN: CountdownState(app),
            GameStateType.PLAYING: PlayingState(app),
            GameStateType.GAME_OVER: GameOverState(app)
        }
        
    @property
    def current_state(self):
        return self.states[self.current_state_type]
        
    def handle_event(self, event):
        """Process event and potentially transition state."""
        new_state = self.current_state.handle_event(event)
        if new_state:
            self.current_state_type = new_state
            
    def update(self):
        """Update current state and check for transitions."""
        new_state = self.current_state.update()
        if new_state:
            self.current_state_type = new_state
            
    def draw(self, screen):
        """Draw current state UI."""
        self.current_state.draw(screen)
        
    def is_playing(self):
        return self.current_state_type == GameStateType.PLAYING
        
    def is_game_over(self):
        return self.current_state_type == GameStateType.GAME_OVER