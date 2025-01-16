from anyio import create_task_group, create_memory_object_stream, Event, CancelScope
from typing import AsyncGenerator, Dict, Any, Callable, List
from saga.effects import *


class SagaRuntime:
    def __init__(self):
        self.store = None
        self._action_sender, self._action_receiver = create_memory_object_stream[Dict](100)
        self.error_handlers = []
        self._running_sagas = set()

    async def run(self, saga: Callable[..., AsyncGenerator], *args, **kwargs):
        """Run a saga generator function."""
        async with create_task_group() as tg:
            await tg.start(self._run_saga, saga, args, kwargs)

    async def _run_saga(self, saga_fn, args, kwargs, *, task_status=None):
        """Run a saga generator function and handle its effects."""
        try:
            gen = saga_fn(*args)  # Don't pass kwargs to saga functions
            result = None
            while True:
                try:
                    effect = await gen.asend(result)
                    result = await self._handle_effect(effect)
                except StopAsyncIteration:
                    break
        except Exception as e:
            await self._handle_error(e)
        if task_status is not None:
            task_status.started()

    async def _handle_effect(self, effect: Effect, task_status=None) -> Any:
        if task_status is not None:
            task_status.started()
        """Handle a saga effect."""
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
                async with create_task_group() as tg:
                    await tg.start(self._run_saga, saga, (), {})
                return None

            case All(effects):
                results = [None] * len(effects)  # Pre-allocate list with correct size

                async def wrapper(_effect, idx):
                    result = await self._handle_effect(_effect)
                    results[idx] = result

                async with create_task_group() as tg:
                    for idx, effect in enumerate(effects):
                        tg.start_soon(wrapper, effect, idx)

                return results

            case Race(effects):
                return await self._handle_race(effects)

    async def dispatch(self, action: Dict[str, Any]) -> None:
        """Dispatch an action to the store and action stream."""
        if self.store:
            self.store.dispatch(action)
        await self._action_sender.send(action)

    async def _take(self, pattern: str = None) -> Dict[str, Any]:
        """Take an action from the action stream that matches the pattern."""
        while True:
            action = await self._action_receiver.receive()
            if pattern is None or action["type"] == pattern:
                return action

    async def _handle_race(self, effects: Dict[str, Effect]) -> Dict[str, Any]:
        """Handle racing between multiple effects."""
        done = Event()
        result = {}

        async def run_effect(key: str, effect: Effect, *, task_status=None):
            if task_status is not None:
                task_status.started()
            try:
                with CancelScope() as scope:
                    value = await self._handle_effect(effect)
                    if not done.is_set():
                        result[key] = value
                        done.set()
            except Exception as e:
                if not done.is_set():
                    await self._handle_error(e)
                    done.set()

        async with create_task_group() as tg:
            for key, effect in effects.items():
                tg.start_soon(run_effect, key, effect)
            await done.wait()

        return result

    async def _handle_error(self, error: Exception):
        """Handle errors in sagas."""
        for handler in self.error_handlers:
            try:
                await handler(error)
            except Exception:
                pass  # Ignore errors in error handlers
        if not self.error_handlers:
            raise error  # Re-raise if no handlers

    def set_store(self, store):
        """Set the Redux store for state management."""
        self.store = store

    def add_error_handler(self, handler):
        """Add an error handler for saga errors."""
        self.error_handlers.append(handler)