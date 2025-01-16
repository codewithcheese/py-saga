import pytest
import asyncio
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

@pytest.mark.asyncio
async def test_basic_saga_workflow():
    """Test a basic saga that increments a counter"""
    done = asyncio.Event()
    
    async def increment_saga():
        # Take an INCREMENT_REQUESTED action
        yield Take("INCREMENT_REQUESTED")
        # Put an INCREMENT action
        yield Put({"type": "INCREMENT"})
        # Select the current state
        state = yield Select(lambda s: s["counter"])
        assert state == 1
        done.set()
        
    runtime = SagaRuntime()
    runtime.store = MockStore({"counter": 0})
    
    async with asyncio.TaskGroup() as tg:
        tg.create_task(runtime.run(increment_saga))
        # Dispatch an action
        await runtime.dispatch({"type": "INCREMENT_REQUESTED", "extra": "data"})
        # Wait for saga to complete
        await done.wait()
        
@pytest.mark.asyncio
async def test_parallel_effects():
    """Test running multiple effects in parallel using All"""
    done = asyncio.Event()
    
    async def delay(ms):
        await asyncio.sleep(ms / 1000)
        return ms

    async def parallel_saga():
        results = yield All([
            Call(delay, 10),
            Call(delay, 20),
            Call(delay, 30)
        ])
        assert results == [10, 20, 30]
        done.set()
        
    runtime = SagaRuntime()
    async with asyncio.TaskGroup() as tg:
        await tg.create_task(runtime.run(parallel_saga))
        await done.wait()

@pytest.mark.asyncio
async def test_race_condition():
    """Test racing between multiple effects"""
    done = asyncio.Event()
    
    async def slow_increment():
        await asyncio.sleep(0.1)
        return "SLOW"
    
    async def fast_increment():
        return "FAST"
    
    async def race_saga():
        result = yield Race({
            "slow": Call(slow_increment),
            "fast": Call(fast_increment)
        })
        assert "fast" in result
        assert result["fast"] == "FAST"
        done.set()
        
    runtime = SagaRuntime()
    async with asyncio.TaskGroup() as tg:
        await tg.create_task(runtime.run(race_saga))
        await done.wait()

@pytest.mark.asyncio
async def test_fork_saga():
    """Test forking a child saga"""
    parent_done = asyncio.Event()
    child_done = asyncio.Event()
    
    async def child_saga():
        yield Take("CHILD_ACTION")
        child_done.set()
    
    async def parent_saga():
        yield Fork(child_saga)
        parent_done.set()
        
    runtime = SagaRuntime()
    async with asyncio.TaskGroup() as tg:
        await tg.create_task(runtime.run(parent_saga))
        await parent_done.wait()
        await runtime.dispatch({"type": "CHILD_ACTION"})
        await child_done.wait()
