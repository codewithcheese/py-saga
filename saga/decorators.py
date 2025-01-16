from functools import wraps
from typing import AsyncGenerator


def saga(func):
    """Decorator to mark generator functions as sagas"""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> AsyncGenerator:
        gen = func(*args, **kwargs)
        while True:
            try:
                effect = await gen.__anext__()
                yield effect
            except StopAsyncIteration:
                break

    return wrapper