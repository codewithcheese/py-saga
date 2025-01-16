import asyncio
from asyncio import Queue, TaskGroup, Event, Task, create_task
from typing import AsyncGenerator, Dict, Any, Callable, List, Union, Type
from saga.effects import *
from saga.actions import Action
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SagaRuntime:
    """Runtime for executing sagas with Redux-style effects."""
    
    def __init__(self, store = None):
        self.store = store
        self._action_queue = Queue[Action](maxsize=100)
        self.error_handlers = []
        self._running_sagas = set()

    async def dispatch(self, action: Action) -> None:
        """Dispatch an action to the store and action stream."""
        logger.debug(f"Dispatching action: {action}")
        if self.store:
            self.store.dispatch(action)
        await self._action_queue.put(action)

    async def _take(self, pattern: Union[str, Type[Action]] = None) -> Action:
        """Take an action from the action stream that matches the pattern."""
        logger.debug(f"Taking action with pattern: {pattern}")
        while True:
            action = await self._action_queue.get()
            logger.debug(f"Got action from queue: {action}")
            if pattern is None:
                logger.debug("No pattern, returning action")
                self._action_queue.task_done()
                return action
            elif isinstance(pattern, str) and action.type == pattern:
                logger.debug(f"Pattern {pattern} matches action type")
                self._action_queue.task_done()
                return action
            elif isinstance(pattern, type) and isinstance(action, pattern):
                logger.debug(f"Action {action} matches pattern type {pattern}")
                self._action_queue.task_done()
                return action
            logger.debug(f"Action {action} doesn't match pattern {pattern}, continuing")

    async def run(self, saga: Callable[..., AsyncGenerator], *args, **kwargs):
        """Run a saga generator function."""
        logger.debug(f"Running saga: {saga.__name__}")
        async with TaskGroup() as tg:
            await tg.create_task(self._run_saga(saga, args, kwargs))

    async def _run_saga(self, saga_fn, args, kwargs):
        """Run a saga generator function and handle its effects."""
        logger.debug(f"Starting saga function: {saga_fn.__name__}")
        try:
            gen = saga_fn(*args, **kwargs)
            effect = await gen.__anext__()
            while True:
                try:
                    logger.debug(f"Handling effect: {effect}")
                    result = await self._handle_effect(effect)
                    logger.debug(f"Effect result: {result}")
                    effect = await gen.asend(result)
                except StopAsyncIteration:
                    logger.debug("Saga completed")
                    break
        except Exception as e:
            logger.error(f"Saga error: {e}", exc_info=True)
            await self._handle_error(e)

    async def _handle_effect(self, effect: Effect) -> Any:
        """Handle different types of effects."""
        match effect:
            case Call(fn, args, kwargs):
                logger.debug(f"Handling Call effect: {fn.__name__}")
                return await fn(*args, **(kwargs or {}))

            case Put(action):
                logger.debug(f"Handling Put effect: {action}")
                if not self.store:
                    raise RuntimeError("Cannot use Put effect without a store")
                await self.dispatch(action)
                return action

            case Take(pattern):
                logger.debug(f"Handling Take effect with pattern: {pattern}")
                return await self._take(pattern)

            case Select(selector):
                logger.debug("Handling Select effect")
                if not self.store:
                    raise RuntimeError("Cannot use Select effect without a store")
                state = self.store.get_state()
                return selector(state) if selector else state

            case Fork(saga):
                async with TaskGroup() as tg:
                    tg.create_task(self._run_saga(saga, (), {}))
                return None

            case All(effects):
                logger.debug(f"Handling All effect with {len(effects)} effects")
                results = [None] * len(effects)
                async def wrapper(_effect, idx):
                    results[idx] = await self._handle_effect(_effect)
                async with TaskGroup() as tg:
                    for i, effect in enumerate(effects):
                        tg.create_task(wrapper(effect, i))
                return results

            case Race(effects):
                logger.debug(f"Handling Race effect with {len(effects)} effects")
                return await self._handle_race(effects)

            case _:
                raise ValueError(f"Unknown effect type: {effect}")

    async def _handle_error(self, error: Exception):
        """Handle saga errors."""
        logger.error(f"Handling error: {error}")
        for handler in self.error_handlers:
            await handler(error)
        raise error

    async def _handle_race(self, effects: Dict[str, Effect]) -> Dict[str, Any]:
        """Handle race between multiple effects."""
        logger.debug(f"Starting race between {len(effects)} effects")
        done = Event()
        results = {}

        async def run_effect(key: str, effect: Effect):
            try:
                results[key] = await self._handle_effect(effect)
                done.set()
            except Exception as e:
                results[key] = e
                done.set()

        async with TaskGroup() as tg:
            for key, effect in effects.items():
                tg.create_task(run_effect(key, effect))
            await done.wait()

        return results

    def set_store(self, store):
        """Set the Redux store for state management."""
        self.store = store

    def add_error_handler(self, handler):
        """Add an error handler for saga errors."""
        self.error_handlers.append(handler)