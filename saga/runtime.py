from anyio import create_task_group, create_memory_object_stream, Event, CancelScope
from typing import AsyncGenerator, Dict, Any, Callable
from saga.effects import *


class SagaRuntime:
    def __init__(self):
        self.store = None
        self.action_stream = None
        self.error_handlers = []
        self._running_sagas = set()

    async def run(self, saga: Callable[..., AsyncGenerator], *args, **kwargs):
        """Run a saga generator function."""
        if self.action_stream is None:
            sender, receiver = create_memory_object_stream[Dict](100)
            self.action_stream = receiver
            self._action_sender = sender

        async with create_task_group() as tg:
            await tg.start(self._run_saga, saga, args, kwargs)

    async def _run_saga(self, saga_fn, args, kwargs, *, task_status=None):
        """Run a saga generator function and handle its effects."""
        try:
            gen = saga_fn(*args)  # Don't pass kwargs to saga functions
            while True:
                try:
                    effect = await gen.__anext__()
                    result = await self._handle_effect(effect)
                    try:
                        await gen.asend(result)
                    except StopAsyncIteration:
                        break
                except StopAsyncIteration:
                    break
        except Exception as e:
            await self._handle_error(e)
        if task_status is not None:
            task_status.started()

    async def _handle_effect(self, effect: Effect) -> Any:
        """Handle a saga effect."""
        match effect:
            case Call(fn, args, kwargs):
                return await fn(*args, **(kwargs or {}))

            case Put(action):
                await self._action_sender.send(action)
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
                async with create_task_group() as tg:
                    results = []
                    for effect in effects:
                        results.append(
                            await tg.start(self._handle_effect, effect)
                        )
                    return results

            case Race(effects):
                return await self._handle_race(effects)

    async def _take(self, pattern: str) -> Dict:
        """Wait for an action matching the pattern."""
        while True:
            action = await self.action_stream.receive()
            if isinstance(pattern, str) and action["type"] == pattern:
                return action
            elif callable(pattern) and pattern(action):
                return action

    async def _handle_race(self, effects: Dict[str, Effect]) -> Dict[str, Any]:
        """Handle racing between multiple effects."""
        done = Event()
        results = {}

        async def run_effect(key: str, effect: Effect, *, task_status=None):
            try:
                with CancelScope() as scope:
                    result = await self._handle_effect(effect)
                    if not done.is_set():
                        results[key] = result
                        done.set()
                        scope.cancel()  # Cancel other tasks
            except Exception as e:
                if not done.is_set():
                    await self._handle_error(e)
                    done.set()
            if task_status is not None:
                task_status.started()

        async with create_task_group() as tg:
            for key, effect in effects.items():
                await tg.start(run_effect, key, effect)
            await done.wait()

        return results

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