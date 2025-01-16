# saga_py/effects.py
from typing import TypeVar, Generic, AsyncGenerator, Any
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class Effect(Generic[T]):
    """Base class for all effects"""
    pass


@dataclass
class Call(Effect[T]):
    fn: Any
    args: tuple = ()
    kwargs: dict = None


@dataclass
class Put(Effect[None]):
    action: dict


@dataclass
class Take(Effect[dict]):
    pattern: str


@dataclass
class Select(Effect[T]):
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


