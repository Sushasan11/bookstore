"""Cart HTTP endpoints: GET /cart, POST /cart/items, PUT /cart/items/{item_id}, DELETE /cart/items/{item_id}."""

from fastapi import APIRouter, status

from app.books.repository import BookRepository
from app.cart.repository import CartItemRepository, CartRepository
from app.cart.schemas import CartItemAdd, CartItemResponse, CartItemUpdate, CartResponse
from app.cart.service import CartService
from app.core.deps import CurrentUser, DbSession

router = APIRouter(prefix="/cart", tags=["cart"])


def _make_service(db: DbSession) -> CartService:
    """Instantiate CartService with all repositories bound to the current DB session."""
    return CartService(
        cart_repo=CartRepository(db),
        cart_item_repo=CartItemRepository(db),
        book_repo=BookRepository(db),
    )


@router.get("", response_model=CartResponse)
async def get_cart(db: DbSession, current_user: CurrentUser) -> CartResponse:
    """Return the authenticated user's cart.

    Returns empty items list (not 404) when the user has no cart yet.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    return await service.get_cart(user_id)


@router.post(
    "/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_cart_item(
    body: CartItemAdd, db: DbSession, current_user: CurrentUser
) -> CartItemResponse:
    """Add a book to the user's cart.

    409 CART_BOOK_OUT_OF_STOCK if book has no stock.
    409 CART_ITEM_DUPLICATE if book is already in the cart.
    404 BOOK_NOT_FOUND if the book does not exist.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    item = await service.add_item(user_id, body.book_id, body.quantity)
    return CartItemResponse.model_validate(item)


@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int, body: CartItemUpdate, db: DbSession, current_user: CurrentUser
) -> CartItemResponse:
    """Update the quantity of a cart item.

    404 CART_ITEM_NOT_FOUND if item does not exist.
    403 CART_ITEM_FORBIDDEN if item belongs to another user.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    item = await service.update_item(user_id, item_id, body.quantity)
    return CartItemResponse.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(
    item_id: int, db: DbSession, current_user: CurrentUser
) -> None:
    """Remove an item from the user's cart.

    404 CART_ITEM_NOT_FOUND if item does not exist.
    403 CART_ITEM_FORBIDDEN if item belongs to another user.
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    await service.remove_item(user_id, item_id)
