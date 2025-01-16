# saga_py/effects.py
from typing import TypeVar, Generic, AsyncGenerator, Any, Callable
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class Effect(Generic[T]):
    """Base class for all effects"""
    pass


@dataclass
class Call(Effect[T]):
    fn: Callable
    args: tuple = ()
    kwargs: dict = None

    def __init__(self, fn: Callable, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs if kwargs else None


@dataclass
class Put(Effect[None]):
    action: dict


@dataclass
class Take(Effect[dict]):
    pattern: str


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
