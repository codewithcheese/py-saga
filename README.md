# py_saga

## Explore

Type-Safe Take Patterns:
```python
# Match any action with an order_id field
yield Take[HasField["order_id", str]]()

# Match union of action types
yield Take[Union[Increment, Reset]]()

# Match with predicate
yield Take(Increment, lambda a: a.amount > 0)
```