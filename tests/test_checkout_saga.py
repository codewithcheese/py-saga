
from saga.testing import SagaTester
from saga.effects import *

import anyio

from saga.decorators import saga
from saga.effects import Call, Put, Take, Select, Fork, All, Race




# @saga
# async def checkout_saga(cart_id: str):
#     # Get cart items
#     cart = yield Call(get_cart, cart_id)
#
#     try:
#         # Validate inventory in parallel
#         yield All([
#             Call(validate_item, item)
#             for item in cart.items
#         ])
#
#         # Process payment with timeout
#         result = yield Race({
#             "payment": Call(process_payment, cart.total),
#             "timeout": Call(sleep, 10)
#         })
#
#         if "timeout" in result:
#             yield Put({"type": "PAYMENT_TIMEOUT"})
#             return
#
#         # Create order
#         order = yield Call(create_order, cart, result["payment"])
#
#         # Background tasks
#         yield Fork(send_email_saga(order))
#
#         yield Put({
#             "type": "CHECKOUT_SUCCESS",
#             "payload": order
#         })
#
#     except Exception as e:
#         yield Put({
#             "type": "CHECKOUT_FAILURE",
#             "payload": str(e)
#         })


# async def test_checkout_saga():
#     tester = SagaTester(checkout_saga)
#     await tester.run("cart-1")
#
#     assert isinstance(tester.effects[0], Call)
#     assert isinstance(tester.effects[-1], Put)
#     assert len(tester.effects) == 5