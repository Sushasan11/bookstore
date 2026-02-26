"""Order HTTP endpoints: POST /orders/checkout, GET /orders, GET /orders/{id}, GET /admin/orders."""

from fastapi import APIRouter, status

from app.cart.repository import CartRepository
from app.core.deps import ActiveUser, AdminUser, DbSession
from app.orders.repository import OrderRepository
from app.orders.schemas import CheckoutRequest, OrderResponse
from app.orders.service import MockPaymentService, OrderService

router = APIRouter(prefix="/orders", tags=["orders"])
admin_router = APIRouter(prefix="/admin/orders", tags=["admin"])


def _make_service(db: DbSession) -> OrderService:
    """Instantiate OrderService with all repositories bound to the current DB session."""
    return OrderService(
        order_repo=OrderRepository(db),
        cart_repo=CartRepository(db),
        payment_service=MockPaymentService(),
    )


@router.post(
    "/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED
)
async def checkout(
    body: CheckoutRequest, db: DbSession, current_user: ActiveUser
) -> OrderResponse:
    """Convert the authenticated user's cart into a confirmed order.

    422 ORDER_CART_EMPTY if cart is empty.
    409 ORDER_INSUFFICIENT_STOCK if any item lacks stock.
    402 ORDER_PAYMENT_FAILED if payment is declined.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    order = await service.checkout(user_id, body)
    return OrderResponse.model_validate(order)


@router.get("", response_model=list[OrderResponse])
async def list_orders(db: DbSession, current_user: ActiveUser) -> list[OrderResponse]:
    """Return the authenticated user's order history with line items."""
    user_id = int(current_user["sub"])
    service = _make_service(db)
    orders = await service.list_for_user(user_id)
    return [OrderResponse.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int, db: DbSession, current_user: ActiveUser
) -> OrderResponse:
    """Return a specific order owned by the authenticated user.

    404 ORDER_NOT_FOUND if order does not exist or belongs to another user.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    order = await service.get_order(user_id, order_id)
    return OrderResponse.model_validate(order)


@admin_router.get("", response_model=list[OrderResponse])
async def list_all_orders(db: DbSession, _: AdminUser) -> list[OrderResponse]:
    """Return all orders across all users (admin only)."""
    service = _make_service(db)
    orders = await service.list_all()
    return [OrderResponse.model_validate(o) for o in orders]
