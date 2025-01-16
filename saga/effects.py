from typing import TypeVar, Generic, AsyncGenerator, Any, Type, Union
from dataclasses import dataclass
from .actions import Action

T = TypeVar('T')


class Effect(Generic[T]):
    """Base class for all effects"""
    pass


@dataclass
class Call(Effect[T]):
    fn: Any
    args: tuple = ()
    kwargs: dict = None

    def __init__(self, fn: Any, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs if kwargs else None


@dataclass
class Put(Effect[None]):
    action: Action


@dataclass
class Take(Effect[Action]):
    pattern: Union[str, Type[Action]]  # Can be string for backward compatibility or action class


@dataclass
class Select(Effect[Any]):
    selector: callable = None


@dataclass
class Fork(Effect[None]):
    saga: AsyncGenerator


@dataclass
class All(Effect[list]):
    effects: list[Effect]


@dataclass
class Race(Effect[dict]):
    effects: dict[str, Effect]
