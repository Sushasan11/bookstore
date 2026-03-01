"""Order HTTP endpoints: POST /orders/checkout, GET /orders, GET /orders/{id}, GET /admin/orders."""

from fastapi import APIRouter, BackgroundTasks, status

from app.cart.repository import CartRepository
from app.core.deps import ActiveUser, AdminUser, DbSession
from app.email.service import EmailSvc
from app.orders.repository import OrderRepository
from app.orders.schemas import CheckoutRequest, OrderResponse
from app.orders.service import MockPaymentService, OrderService
from app.users.repository import UserRepository

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
    body: CheckoutRequest,
    db: DbSession,
    current_user: ActiveUser,
    background_tasks: BackgroundTasks,
    email_svc: EmailSvc,
) -> OrderResponse:
    """Convert the authenticated user's cart into a confirmed order.

    422 ORDER_CART_EMPTY if cart is empty.
    409 ORDER_INSUFFICIENT_STOCK if any item lacks stock.
    402 ORDER_PAYMENT_FAILED if payment is declined.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    order = await service.checkout(user_id, body)

    # Build response first — total_price is a computed field on OrderResponse, not on ORM
    order_response = OrderResponse.model_validate(order)

    # Enqueue confirmation email (post-commit via BackgroundTasks — EMAL-06 safe)
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user:
        email_svc.enqueue(
            background_tasks,
            to=user.email,
            template_name="order_confirmation.html",
            subject="Your Bookstore order is confirmed",
            context={
                "customer_name": user.email.split("@")[0].title(),
                "order_id": order.id,
                "items": [
                    {
                        "title": item.book.title if item.book else "Unknown Book",
                        "author": item.book.author if item.book else "",
                        "quantity": item.quantity,
                        "unit_price": f"{item.unit_price:.2f}",
                        "cover_image_url": item.book.cover_image_url if item.book else None,
                    }
                    for item in order.items
                ],
                "total_price": f"{order_response.total_price:.2f}",
            },
        )

    return order_response


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
