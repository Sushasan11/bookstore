"""Business logic for the orders feature: checkout orchestration and payment."""

import random

from app.cart.repository import CartRepository
from app.core.exceptions import AppError
from app.orders.models import Order
from app.orders.repository import OrderRepository
from app.orders.schemas import CheckoutRequest, InsufficientStockItem


class MockPaymentService:
    """Simulates a payment gateway — 90% success rate with deterministic test override."""

    async def charge(self, *, force_fail: bool = False) -> bool:
        """Process a payment. Returns True on success, False on decline."""
        if force_fail:
            return False
        return random.random() > 0.10


class OrderService:
    """Orchestrates checkout: lock books, validate stock, payment, create order, clear cart."""

    def __init__(
        self,
        order_repo: OrderRepository,
        cart_repo: CartRepository,
        payment_service: MockPaymentService,
    ) -> None:
        self.order_repo = order_repo
        self.cart_repo = cart_repo
        self.payment_service = payment_service

    async def checkout(self, user_id: int, request: CheckoutRequest) -> Order:
        """Convert the user's cart into a confirmed order.

        Raises:
            AppError(422) ORDER_CART_EMPTY if cart is empty or does not exist.
            AppError(409) ORDER_INSUFFICIENT_STOCK if any item lacks stock.
            AppError(402) ORDER_PAYMENT_FAILED if payment is declined.
        """
        # Step 1: Load cart
        cart = await self.cart_repo.get_with_items(user_id)
        if cart is None or not cart.items:
            raise AppError(422, "Cart is empty", "ORDER_CART_EMPTY")

        # Step 2: Sort book IDs ascending (deadlock prevention)
        book_ids = sorted(item.book_id for item in cart.items)

        # Step 3: Lock books with SELECT FOR UPDATE
        books = await self.order_repo.lock_books(book_ids)
        book_map = {b.id: b for b in books}

        # Step 4: Validate stock for ALL items before any mutation
        insufficient: list[InsufficientStockItem] = []
        for item in cart.items:
            book = book_map[item.book_id]
            if book.stock_quantity < item.quantity:
                insufficient.append(
                    InsufficientStockItem(
                        book_id=item.book_id,
                        title=book.title,
                        requested=item.quantity,
                        available=book.stock_quantity,
                    )
                )
        if insufficient:
            detail = "Insufficient stock for one or more items"
            raise AppError(409, detail, "ORDER_INSUFFICIENT_STOCK")

        # Step 5: Attempt payment
        paid = await self.payment_service.charge(
            force_fail=request.force_payment_failure
        )
        if not paid:
            raise AppError(402, "Payment declined", "ORDER_PAYMENT_FAILED")

        # Step 6: Create order (decrements stock inside)
        order = await self.order_repo.create_order(user_id, cart.items, book_map)

        # Step 7: Clear cart items (cart row itself is preserved)
        # Snapshot items list before deletion to avoid iterating a mutating collection
        items_to_delete = list(cart.items)
        for item in items_to_delete:
            await self.cart_repo.session.delete(item)
        await self.cart_repo.session.flush()
        # Expire the cart so subsequent reads reload items from DB, not the identity map
        self.cart_repo.session.expire(cart)

        return order

    async def list_for_user(self, user_id: int) -> list[Order]:
        """Return all orders for the given user."""
        return await self.order_repo.list_for_user(user_id)

    async def get_order(self, user_id: int, order_id: int) -> Order:
        """Return a specific order owned by the user.

        Raises:
            AppError(404) ORDER_NOT_FOUND if not found or not owned by user.
        """
        order = await self.order_repo.get_by_id_for_user(order_id, user_id)
        if order is None:
            raise AppError(404, "Order not found", "ORDER_NOT_FOUND")
        return order

    async def list_all(self) -> list[Order]:
        """Return all orders (admin view)."""
        return await self.order_repo.list_all()
