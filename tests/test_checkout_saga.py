from saga.example import checkout_saga
from saga.testing import SagaTester
from saga.effects import *


# async def test_checkout_saga():
#     tester = SagaTester(checkout_saga)
#     await tester.run("cart-1")
#
#     assert isinstance(tester.effects[0], Call)
#     assert isinstance(tester.effects[-1], Put)
#     assert len(tester.effects) == 5