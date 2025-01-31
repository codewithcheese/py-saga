from typing import Dict, Any
from .actions import Action

class Store:
    """Simple store for state management."""
    
    def __init__(self, initial_state: Dict[str, Any] = None):
        self.state = initial_state or {}

    def get_state(self) -> Dict[str, Any]:
        return self.state

    def dispatch(self, action: Action) -> Action:
        """Process an action. Override this method to implement state updates."""
        return action
