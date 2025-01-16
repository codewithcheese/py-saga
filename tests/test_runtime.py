import pytest
import asyncio
from typing import Dict, Any
from saga.runtime import SagaRuntime
from saga.effects import Call, Put, Take, Select, Fork, All, Race
from saga.store import Store
from saga.actions import Action, Increment, Decrement
from dataclasses import dataclass

# Mock store for testing
@dataclass
class IncrementRequested(Action):
    pass

class MockStore(Store):
    def __init__(self, state=None):
        self.state = state if state else {}

    def dispatch(self, action: Action) -> Action:
        match action:
            case Increment(amount=amount):
                self.state["counter"] = self.state.get("counter", 0) + amount
            case Decrement(amount=amount):
                self.state["counter"] = self.state.get("counter", 0) - amount
        return action

@pytest.mark.asyncio
async def test_basic_saga_workflow():
    """Test a basic saga that increments a counter"""
    done = asyncio.Event()
    
    async def increment_saga():
        # Take an INCREMENT_REQUESTED action
        yield Take(IncrementRequested)
        # Put an INCREMENT action
        yield Put(Increment(amount=1))
        # Select the current state
        state = yield Select(lambda s: s["counter"])
        assert state == 1
        done.set()
        
    store = MockStore({"counter": 0})
    runtime = SagaRuntime(store)
    
    async with asyncio.TaskGroup() as tg:
        tg.create_task(runtime.run(increment_saga))
        # Dispatch an action
        await runtime.dispatch(IncrementRequested())
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
        
    runtime = SagaRuntime()  # No store needed for Call effects
    async with asyncio.TaskGroup() as tg:
        tg.create_task(runtime.run(parallel_saga))
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
        
    runtime = SagaRuntime()  # No store needed for Call effects
    async with asyncio.TaskGroup() as tg:
        tg.create_task(runtime.run(race_saga))
        await done.wait()

@dataclass
class StartFork(Action):
    pass

@dataclass
class ForkStarted(Action):
    pass

@dataclass
class ForkCompleted(Action):
    pass

@pytest.mark.asyncio
async def test_fork_saga():
    """Test forking a saga"""
    done = asyncio.Event()
    
    async def child_saga():
        yield Put(ForkStarted())
        yield Put(ForkCompleted())
    
    async def parent_saga():
        yield Take(StartFork)
        yield Fork(child_saga)
        yield Take(ForkCompleted)
        done.set()
    
    store = MockStore()
    runtime = SagaRuntime(store)
    
    async with asyncio.TaskGroup() as tg:
        tg.create_task(runtime.run(parent_saga))
        await runtime.dispatch(StartFork())
        await done.wait()
