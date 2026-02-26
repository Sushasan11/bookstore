"""Review HTTP endpoints: POST /books/{book_id}/reviews, GET /books/{book_id}/reviews, GET /reviews/{review_id}."""

from fastapi import APIRouter, Query, status

from app.books.repository import BookRepository
from app.core.deps import ActiveUser, DbSession
from app.orders.repository import OrderRepository
from app.reviews.repository import ReviewRepository
from app.reviews.schemas import ReviewCreate, ReviewListResponse, ReviewResponse
from app.reviews.service import ReviewService

router = APIRouter(tags=["reviews"])


def _make_service(db: DbSession) -> ReviewService:
    """Instantiate ReviewService with all repositories bound to the current DB session."""
    return ReviewService(
        review_repo=ReviewRepository(db),
        order_repo=OrderRepository(db),
        book_repo=BookRepository(db),
    )


@router.post(
    "/books/{book_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    book_id: int,
    body: ReviewCreate,
    db: DbSession,
    current_user: ActiveUser,
) -> ReviewResponse:
    """Create a review for a book.

    Requires authentication. The user must have a confirmed purchase of the book.

    403 NOT_PURCHASED if the user has not purchased the book.
    404 BOOK_NOT_FOUND if the book does not exist.
    409 DUPLICATE_REVIEW if the user has already reviewed this book (includes existing_review_id).
    """
    user_id = int(current_user["sub"])
    service = _make_service(db)
    review, verified_purchase = await service.create(user_id, book_id, body.rating, body.text)
    return ReviewResponse.model_validate(service._build_review_data(review, verified_purchase))


@router.get("/books/{book_id}/reviews", response_model=ReviewListResponse)
async def list_reviews(
    book_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> ReviewListResponse:
    """Return paginated reviews for a book.

    Public endpoint — no authentication required.
    Each review includes a verified_purchase flag indicating confirmed purchase.
    """
    service = _make_service(db)
    items_with_vp, total = await service.list_for_book(book_id, page, size)
    items = [
        ReviewResponse.model_validate(service._build_review_data(r, vp))
        for r, vp in items_with_vp
    ]
    return ReviewListResponse(items=items, total=total, page=page, size=size)


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: DbSession,
) -> ReviewResponse:
    """Return a single review by ID.

    Public endpoint — no authentication required.
    404 REVIEW_NOT_FOUND if the review does not exist or has been soft-deleted.
    """
    service = _make_service(db)
    review, verified_purchase = await service.get(review_id)
    return ReviewResponse.model_validate(service._build_review_data(review, verified_purchase))
