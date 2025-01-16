from typing import List, Any

from saga.effects import Effect


class SagaTester:
    """Utility for testing sagas"""

    def __init__(self, saga):
        self.saga = saga
        self.effects: List[Effect] = []
        self.results: List[Any] = []

    async def run(self, *args, **kwargs):
        async for effect in self.saga(*args, **kwargs):
            self.effects.append(effect)
            result = self._mock_effect(effect)
            self.results.append(result)
            try:
                await self.saga.asend(result)
            except StopAsyncIteration:
                break

    def _mock_effect(self, effect: Effect) -> Any:
        # Mock effect results for testing
        pass
