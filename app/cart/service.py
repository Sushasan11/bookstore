"""Business logic for the cart feature: stock validation, ownership enforcement."""

from app.books.repository import BookRepository
from app.cart.models import CartItem
from app.cart.repository import CartItemRepository, CartRepository
from app.cart.schemas import CartItemResponse, CartResponse
from app.core.exceptions import AppError


class CartService:
    """Orchestrates cart operations with stock validation and ownership checks."""

    def __init__(
        self,
        cart_repo: CartRepository,
        cart_item_repo: CartItemRepository,
        book_repo: BookRepository,
    ) -> None:
        self.cart_repo = cart_repo
        self.cart_item_repo = cart_item_repo
        self.book_repo = book_repo

    async def get_cart(self, user_id: int) -> CartResponse:
        """Return the user's cart. Returns empty items list if no cart exists yet.

        Does NOT create a DB row on GET — only POST /cart/items creates the cart.
        """
        cart = await self.cart_repo.get_with_items(user_id)
        if cart is None:
            return CartResponse(items=[])
        return CartResponse(
            items=[CartItemResponse.model_validate(item) for item in cart.items]
        )

    async def add_item(self, user_id: int, book_id: int, quantity: int) -> CartItem:
        """Add a book to the user's cart.

        Raises:
            AppError(404) if book does not exist.
            AppError(409) CART_BOOK_OUT_OF_STOCK if book.stock_quantity == 0.
            AppError(409) CART_ITEM_DUPLICATE if book already in cart.
        """
        book = await self.book_repo.get_by_id(book_id)
        if book is None:
            raise AppError(404, "Book not found", "BOOK_NOT_FOUND", "book_id")

        if book.stock_quantity == 0:
            raise AppError(
                409,
                "This book is out of stock and cannot be added to cart",
                "CART_BOOK_OUT_OF_STOCK",
                "book_id",
            )

        cart = await self.cart_repo.get_or_create(user_id)
        return await self.cart_item_repo.add(cart.id, book_id, quantity)

    async def update_item(self, user_id: int, item_id: int, quantity: int) -> CartItem:
        """Update the quantity of a cart item the user owns.

        Raises:
            AppError(404) if item does not exist.
            AppError(403) CART_ITEM_FORBIDDEN if item belongs to another user.
        """
        item = await self._get_item_for_user(item_id, user_id)
        return await self.cart_item_repo.update_quantity(item, quantity)

    async def remove_item(self, user_id: int, item_id: int) -> None:
        """Remove a cart item the user owns.

        Raises:
            AppError(404) if item does not exist.
            AppError(403) CART_ITEM_FORBIDDEN if item belongs to another user.
        """
        item = await self._get_item_for_user(item_id, user_id)
        await self.cart_item_repo.delete(item)

    async def _get_item_for_user(self, item_id: int, user_id: int) -> CartItem:
        """Fetch cart item and verify ownership.

        Raises:
            AppError(404) CART_ITEM_NOT_FOUND if item does not exist.
            AppError(403) CART_ITEM_FORBIDDEN if item belongs to another user.
        """
        item = await self.cart_item_repo.get_by_id(item_id)
        if item is None:
            raise AppError(404, "Cart item not found", "CART_ITEM_NOT_FOUND", "item_id")
        if item.cart.user_id != user_id:
            raise AppError(
                403,
                "Not authorized to modify this cart item",
                "CART_ITEM_FORBIDDEN",
            )
        return item
