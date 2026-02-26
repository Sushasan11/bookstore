"""Business logic for the reviews feature.

Enforces:
- Book existence (404 BOOK_NOT_FOUND)
- Duplicate review detection (409 DUPLICATE_REVIEW via DuplicateReviewError)
- Purchase gate (403 NOT_PURCHASED)
- verified_purchase computation per review
"""

from app.books.repository import BookRepository
from app.core.exceptions import AppError, DuplicateReviewError
from app.orders.repository import OrderRepository
from app.reviews.models import Review
from app.reviews.repository import ReviewRepository


class ReviewService:
    """Orchestrates review operations with purchase gate and duplicate detection."""

    def __init__(
        self,
        review_repo: ReviewRepository,
        order_repo: OrderRepository,
        book_repo: BookRepository,
    ) -> None:
        self.review_repo = review_repo
        self.order_repo = order_repo
        self.book_repo = book_repo

    async def create(
        self,
        user_id: int,
        book_id: int,
        rating: int,
        text: str | None,
    ) -> tuple[Review, bool]:
        """Create a new review for a book.

        Returns (review, verified_purchase) where verified_purchase is True
        because the purchase gate must pass before creation.

        Raises:
            AppError(404) BOOK_NOT_FOUND if the book does not exist.
            DuplicateReviewError if user has already reviewed this book.
            AppError(403) NOT_PURCHASED if user has not purchased the book.
        """
        # 1. Verify book exists
        book = await self.book_repo.get_by_id(book_id)
        if book is None:
            raise AppError(404, "Book not found", "BOOK_NOT_FOUND", "book_id")

        # 2. Pre-check for duplicate — avoids IntegrityError and enables enriched 409
        existing = await self.review_repo.get_by_user_and_book(user_id, book_id)
        if existing is not None:
            raise DuplicateReviewError(existing.id)

        # 3. Enforce purchase gate
        purchased = await self.order_repo.has_user_purchased_book(user_id, book_id)
        if not purchased:
            raise AppError(
                403,
                "You must purchase this book before submitting a review",
                "NOT_PURCHASED",
                "book_id",
            )

        # 4. Create the review
        review = await self.review_repo.create(user_id, book_id, rating, text)

        # 5. verified_purchase is always True here — purchase gate passed
        return review, True

    async def list_for_book(
        self,
        book_id: int,
        page: int,
        size: int,
    ) -> tuple[list[tuple[Review, bool]], int]:
        """Return paginated reviews with verified_purchase flag for each.

        N+1 queries for verified_purchase are accepted for page sizes up to 20
        (documented known limitation).

        Returns ([(review, verified_purchase), ...], total).
        """
        reviews, total = await self.review_repo.list_for_book(
            book_id, page=page, size=size
        )
        items_with_vp: list[tuple[Review, bool]] = []
        for review in reviews:
            vp = await self.order_repo.has_user_purchased_book(
                review.user_id, review.book_id
            )
            items_with_vp.append((review, vp))
        return items_with_vp, total

    async def get(self, review_id: int) -> tuple[Review, bool]:
        """Fetch a single review by ID with verified_purchase flag.

        Raises:
            AppError(404) REVIEW_NOT_FOUND if not found or soft-deleted.
        """
        review = await self.review_repo.get_by_id(review_id)
        if review is None:
            raise AppError(404, "Review not found", "REVIEW_NOT_FOUND")

        vp = await self.order_repo.has_user_purchased_book(
            review.user_id, review.book_id
        )
        return review, vp

    def _build_review_data(self, review: Review, verified_purchase: bool) -> dict:
        """Construct a plain dict suitable for ReviewResponse.model_validate().

        Builds nested author and book summaries explicitly because the ORM
        field names differ from the schema field names (e.g. book.id -> book_id,
        user.email -> display_name).
        """
        return {
            "id": review.id,
            "book_id": review.book_id,
            "user_id": review.user_id,
            "rating": review.rating,
            "text": review.text,
            "verified_purchase": verified_purchase,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "author": {
                "user_id": review.user.id,
                "display_name": review.user.email.split("@")[0],
                "avatar_url": None,
            },
            "book": {
                "book_id": review.book.id,
                "title": review.book.title,
                "cover_image_url": review.book.cover_image_url,
            },
        }
