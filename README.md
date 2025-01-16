# py-saga

A modern Python implementation of the Redux-Saga pattern, leveraging Python's native features for elegant task orchestration.

## Why py-saga?

py_saga brings the power of Redux-Saga to Python, but with a distinctly Pythonic feel:

- **Type-Safe Actions**: Uses dataclasses for type-safe, auto-completing actions instead of string-based dictionaries
- **Generator-Based Effects**: Leverages Python's async generators for clear, sequential task orchestration
- **Modern AsyncIO**: Built on Python's TaskGroup for robust concurrent execution
- **Pattern Matching**: Uses Python 3.10+ pattern matching for elegant action handling

## Example

```python
from saga.actions import Action
from saga.effects import Take, Put, Fork

# Define type-safe actions
@dataclass
class OrderCreated(Action):
    order_id: str
    amount: float

@dataclass
class PaymentProcessed(Action):
    order_id: str
    status: str

# Define a saga to handle orders
async def process_order_saga():
    # Wait for new orders
    order = yield Take(OrderCreated)
    
    # Process payment in parallel
    yield Fork(process_payment(order.order_id))
    
    # Wait for payment completion
    result = yield Take(PaymentProcessed)
    
    # Handle result
    if result.status == "success":
        yield Put(OrderCompleted(order_id=order.order_id))
```

## Features

- **Parallel Execution**: Fork tasks to run concurrently
- **Race Conditions**: Race between multiple effects
- **Error Handling**: Built-in error propagation and handling
- **State Management**: Optional Redux-style store integration
- **Type Safety**: Full type hints and runtime type checking

## Installation

NOT YET RELEASED

```bash
pip install py-saga
```

## Why It's Cool

Unlike JavaScript's redux-saga, py_saga takes advantage of Python's rich type system and modern features:

1. No more string-based action types - actions are proper classes
2. Pattern matching instead of switch statements
3. Native async/await integration
4. Type hints and IDE support out of the box
5. TaskGroup for proper concurrent execution

Perfect for:
- Task orchestration
- Workflow management
- Event-driven architectures
- Microservice coordination