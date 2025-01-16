import pytest
import anyio
from typing import Dict, Any
from saga.runtime import SagaRuntime
from saga.effects import Call, Put, Take, Select, Fork, All, Race

# Mock store for testing
class MockStore:
    def __init__(self, initial_state: Dict[str, Any] = None):
        self.state = initial_state or {}
        
    def get_state(self):
        return self.state

    def dispatch(self, action):
        if action["type"] == "INCREMENT":
            self.state["counter"] = self.state.get("counter", 0) + 1
        elif action["type"] == "DECREMENT":
            self.state["counter"] = self.state.get("counter", 0) - 1

@pytest.mark.anyio
async def test_basic_saga_workflow():
    """Test a basic saga that increments a counter"""
    async def increment_saga():
        # Take an INCREMENT_REQUESTED action
        action = yield Take("INCREMENT_REQUESTED")
        # Put an INCREMENT action
        yield Put({"type": "INCREMENT"})
        # Select the current state
        state = yield Select(lambda s: s["counter"])
        assert state == 1
        
    runtime = SagaRuntime()
    runtime.store = MockStore({"counter": 0})
    
    async with anyio.create_task_group() as tg:
        # Start the saga
        await tg.start(runtime.run, increment_saga)
        # Dispatch an action
        await runtime.action_stream.send({"type": "INCREMENT_REQUESTED"})
        
@pytest.mark.anyio
async def test_parallel_effects():
    """Test running multiple effects in parallel using All"""
    async def parallel_saga():
        async def task1():
            return "result1"
            
        async def task2():
            return "result2"
            
        results = yield All([
            Call(task1),
            Call(task2)
        ])
        assert results == ["result1", "result2"]
        
    runtime = SagaRuntime()
    await runtime.run(parallel_saga)
    
@pytest.mark.anyio
async def test_race_condition():
    """Test racing between multiple effects"""
    async def race_saga():
        async def slow_task():
            await anyio.sleep(0.1)
            return "slow"
            
        async def fast_task():
            return "fast"
            
        result = yield Race({
            "slow": Call(slow_task),
            "fast": Call(fast_task)
        })
        assert result == {"fast": "fast"}
        
    runtime = SagaRuntime()
    await runtime.run(race_saga)

@pytest.mark.anyio
async def test_fork_saga():
    """Test forking a child saga"""
    results = []
    
    async def child_saga():
        results.append("child")
        yield None  # Must yield at least once to be a generator
        
    async def parent_saga():
        results.append("parent")
        yield Fork(child_saga)
        assert "parent" in results
        assert "child" in results
        
    runtime = SagaRuntime()
    await runtime.run(parent_saga)
