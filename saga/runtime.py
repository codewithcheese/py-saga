import asyncio
from asyncio import Queue, TaskGroup, Event, Task, create_task
from typing import AsyncGenerator, Dict, Any, Callable, List
from saga.effects import *


class SagaRuntime:
    def __init__(self):
        self.store = None
        self._action_queue = Queue[Dict](maxsize=100)
        self.error_handlers = []
        self._running_sagas = set()

    async def dispatch(self, action: Dict[str, Any]) -> None:
        """Dispatch an action to the store and action stream."""
        if self.store:
            self.store.dispatch(action)
        await self._action_queue.put(action)

    async def _take(self, pattern: str = None) -> Dict[str, Any]:
        """Take an action from the action stream that matches the pattern."""
        while True:
            action = await self._action_queue.get()
            if pattern is None or action["type"] == pattern:
                self._action_queue.task_done()
                return action

    async def run(self, saga: Callable[..., AsyncGenerator], *args, **kwargs):
        """Run a saga generator function."""
        async with TaskGroup() as tg:
            await tg.create_task(self._run_saga(saga, args, kwargs))

    async def _run_saga(self, saga_fn, args, kwargs):
        """Run a saga generator function and handle its effects."""
        try:
            gen = saga_fn(*args)  # Don't pass kwargs to saga functions
            effect = await gen.__anext__()  # Get first effect
            while True:
                try:
                    result = await self._handle_effect(effect)
                    effect = await gen.asend(result)
                except StopAsyncIteration:
                    break
        except Exception as e:
            await self._handle_error(e)

    async def _handle_effect(self, effect: Effect) -> Any:
        match effect:
            case Call(fn, args, kwargs):
                return await fn(*args, **(kwargs or {}))

            case Put(action):
                await self.dispatch(action)
                return action

            case Take(pattern):
                return await self._take(pattern)

            case Select(selector):
                state = self.store.get_state()
                return selector(state) if selector else state

            case Fork(saga):
                # Create a new task group just for this fork
                tg = TaskGroup()
                await tg.__aenter__()
                tg.create_task(self._run_saga(saga, (), {}))
                return None

            case All(effects):
                results = [None] * len(effects)

                async def wrapper(_effect, idx):
                    results[idx] = await self._handle_effect(_effect)

                async with TaskGroup() as tg:
                    for i, effect in enumerate(effects):
                        tg.create_task(wrapper(effect, i))
                    await asyncio.sleep(0)  # Let tasks start
                return results

            case Race(effects):
                return await self._handle_race(effects)

    async def _handle_race(self, effects: Dict[str, Effect]) -> Dict[str, Any]:
        """Handle racing between multiple effects."""
        done = Event()
        results: Dict[str, Any] = {}

        async def run_effect(key: str, effect: Effect):
            try:
                result = await self._handle_effect(effect)
                if not done.is_set():
                    results[key] = result
                    done.set()
            except Exception as e:
                if not done.is_set():
                    results[key] = e
                    done.set()

        async with TaskGroup() as tg:
            # Start all tasks
            for key, effect in effects.items():
                tg.create_task(run_effect(key, effect))
            # Wait for first to complete
            await done.wait()

        return results

    async def _handle_error(self, error: Exception):
        """Handle errors in sagas."""
        for handler in self.error_handlers:
            try:
                await handler(error)
                return
            except Exception:
                continue
        raise error  # Re-raise if no handlers

    def set_store(self, store):
        """Set the Redux store for state management."""
        self.store = store

    def add_error_handler(self, handler):
        """Add an error handler for saga errors."""
        self.error_handlers.append(handler)