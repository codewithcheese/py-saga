from dataclasses import dataclass
from typing import ClassVar

@dataclass
class Action:
    """Base class for all actions."""
    type: ClassVar[str]
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'type'):
            cls.type = cls.__name__.upper()

@dataclass
class Increment(Action):
    amount: int = 1

@dataclass
class Decrement(Action):
    amount: int = 1
