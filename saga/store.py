from saga.runtime import SagaRuntime


class Store:
    def __init__(self):
        self.saga_runtime = SagaRuntime()
        self.state = {}

    async def run_saga(self, saga, *args, **kwargs):
        await self.saga_runtime.run(saga, *args, **kwargs)

    async def dispatch(self, action):
        self.state = self.reducer(self.state, action)
        await self.saga_runtime.action_stream.send(action)

