"""Integration tests for Phase 5 Discovery: GET /books (pagination, sort, search, filter)
and GET /books/{id} (detail with in_stock).

Coverage:
  DISC-01: pagination and sorting
  DISC-02: full-text search (FTS) across title and author
  DISC-03: filtering by genre_id and author
  DISC-04: book detail with in_stock boolean

Uses the existing conftest.py async infrastructure:
  - asyncio_mode = "auto" (no @pytest.mark.asyncio needed)
  - client: AsyncClient against the test app
  - db_session: function-scoped with rollback (test isolation)
  - admin_headers: Authorization header for admin-only endpoints
"""

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.repository import UserRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create an admin user and return Authorization headers with a valid bearer token."""
    repo = UserRepository(db_session)
    hashed = await hash_password("adminpass123")
    user = await repo.create(email="discovery_admin@example.com", hashed_password=hashed)
    await repo.set_role_admin(user.id)
    await db_session.flush()

    resp = await client.post(
        "/auth/login",
        json={"email": "discovery_admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_book(client: AsyncClient, admin_headers: dict, **kwargs) -> dict:
    """POST /books and return the created book dict. Raises on non-201."""
    payload = {
        "title": kwargs.get("title", "Untitled"),
        "author": kwargs.get("author", "Unknown Author"),
        "price": kwargs.get("price", "9.99"),
    }
    for key in ("isbn", "genre_id", "description", "cover_image_url", "publish_date"):
        if key in kwargs:
            payload[key] = kwargs[key]
    resp = await client.post("/books", json=payload, headers=admin_headers)
    assert resp.status_code == 201, f"Book creation failed ({resp.status_code}): {resp.json()}"
    return resp.json()


async def _set_stock(client: AsyncClient, admin_headers: dict, book_id: int, quantity: int) -> None:
    """PATCH /books/{id}/stock to set absolute stock quantity."""
    resp = await client.patch(
        f"/books/{book_id}/stock",
        json={"quantity": quantity},
        headers=admin_headers,
    )
    assert resp.status_code == 200, f"Stock update failed: {resp.json()}"


async def _create_genre(client: AsyncClient, admin_headers: dict, name: str) -> dict:
    """POST /genres and return the created genre dict."""
    resp = await client.post("/genres", json={"name": name}, headers=admin_headers)
    assert resp.status_code == 201, f"Genre creation failed: {resp.json()}"
    return resp.json()


# ---------------------------------------------------------------------------
# DISC-01: Pagination and sorting
# ---------------------------------------------------------------------------


async def test_list_books_returns_paginated_envelope(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books returns the expected paginated envelope shape {items, total, page, size}."""
    await _create_book(client, admin_headers, title="Alpha Book", author="Author A", price="10.00")

    resp = await client.get("/books")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert data["page"] == 1
    assert data["size"] == 20  # default


async def test_list_books_empty_result(client: AsyncClient) -> None:
    """GET /books when no books exist returns empty items and zero total."""
    resp = await client.get("/books")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 20


async def test_list_books_default_sort_title(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books without sort param returns books alphabetically by title (A-Z)."""
    await _create_book(client, admin_headers, title="Zephyr Winds", author="Author Z", price="10.00")
    await _create_book(client, admin_headers, title="Apple Orchard", author="Author A", price="10.00")
    await _create_book(client, admin_headers, title="Morning Star", author="Author M", price="10.00")

    resp = await client.get("/books")
    assert resp.status_code == 200
    items = resp.json()["items"]
    titles = [b["title"] for b in items]
    assert titles == sorted(titles), f"Expected sorted titles, got: {titles}"
    assert "Apple Orchard" in titles
    assert titles.index("Apple Orchard") < titles.index("Morning Star")
    assert titles.index("Morning Star") < titles.index("Zephyr Winds")


async def test_list_books_sort_price(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?sort=price returns books in ascending price order."""
    await _create_book(client, admin_headers, title="Expensive Book", author="Author E", price="29.99")
    await _create_book(client, admin_headers, title="Cheap Book", author="Author C", price="4.99")
    await _create_book(client, admin_headers, title="Mid-Price Book", author="Author M", price="14.99")

    resp = await client.get("/books", params={"sort": "price"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    prices = [float(b["price"]) for b in items]
    assert prices == sorted(prices), f"Expected ascending prices, got: {prices}"
    assert prices[0] <= prices[-1]


async def test_list_books_sort_date(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?sort=date returns books in ascending publish_date order (nulls last/first)."""
    await _create_book(
        client, admin_headers, title="Old Book", author="Author O", price="10.00", publish_date="1950-01-01"
    )
    await _create_book(
        client, admin_headers, title="New Book", author="Author N", price="10.00", publish_date="2020-06-15"
    )
    await _create_book(
        client, admin_headers, title="Mid Book", author="Author M", price="10.00", publish_date="1985-03-20"
    )

    resp = await client.get("/books", params={"sort": "date"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    # Extract books with known publish dates and verify order
    dated_items = [b for b in items if b.get("publish_date") is not None]
    dates = [b["publish_date"] for b in dated_items]
    assert dates == sorted(dates), f"Expected ascending dates, got: {dates}"


async def test_list_books_sort_created_at(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?sort=created_at returns 200 with all books; newest-first ordering accepted."""
    b1 = await _create_book(client, admin_headers, title="First Created", author="Author F", price="10.00")
    b2 = await _create_book(client, admin_headers, title="Second Created", author="Author S", price="10.00")
    b3 = await _create_book(client, admin_headers, title="Third Created", author="Author T", price="10.00")

    resp = await client.get("/books", params={"sort": "created_at"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = {b["id"] for b in items}
    # All three books should appear in the result
    assert b1["id"] in ids
    assert b2["id"] in ids
    assert b3["id"] in ids
    # Verify total is accurate
    assert resp.json()["total"] == 3


async def test_list_books_pagination_page_size(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books?page=1&size=2 returns 2 items; page=2&size=2 returns the next batch."""
    # Create 5 books with predictable title sort order
    for i in range(1, 6):
        await _create_book(
            client, admin_headers,
            title=f"Pagination Book {i:02d}",
            author="Paginator",
            price="10.00",
        )

    # Page 1: should have exactly 2 items
    resp1 = await client.get("/books", params={"page": 1, "size": 2})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["items"]) == 2
    assert data1["total"] >= 5
    assert data1["page"] == 1
    assert data1["size"] == 2

    # Page 2: should have 2 different items
    resp2 = await client.get("/books", params={"page": 2, "size": 2})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 2
    assert data2["page"] == 2

    # The two pages must not overlap
    ids_page1 = {b["id"] for b in data1["items"]}
    ids_page2 = {b["id"] for b in data2["items"]}
    assert ids_page1.isdisjoint(ids_page2), "Page 1 and page 2 must have distinct books"


# ---------------------------------------------------------------------------
# DISC-02: Full-text search (FTS)
# ---------------------------------------------------------------------------


async def test_search_by_title_word(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?q=dune returns book with 'Dune' in title."""
    await _create_book(client, admin_headers, title="Dune", author="Frank Herbert", price="15.99")
    await _create_book(client, admin_headers, title="Foundation", author="Isaac Asimov", price="12.99")

    resp = await client.get("/books", params={"q": "dune"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    titles = [b["title"] for b in items]
    assert "Dune" in titles, f"Expected 'Dune' in results for q=dune, got: {titles}"
    assert "Foundation" not in titles


async def test_search_by_title_prefix(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?q=du returns book with 'Dune' in title via prefix match."""
    await _create_book(client, admin_headers, title="Dune", author="Frank Herbert", price="15.99")
    await _create_book(client, admin_headers, title="Neuromancer", author="William Gibson", price="11.99")

    resp = await client.get("/books", params={"q": "du"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    titles = [b["title"] for b in items]
    assert "Dune" in titles, f"Expected prefix 'du' to match 'Dune', got: {titles}"


async def test_search_by_author_name(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?q=tolkien returns book authored by 'J.R.R. Tolkien'."""
    await _create_book(
        client, admin_headers,
        title="The Fellowship of the Ring",
        author="J.R.R. Tolkien",
        price="14.99",
    )
    await _create_book(client, admin_headers, title="Dune", author="Frank Herbert", price="15.99")

    resp = await client.get("/books", params={"q": "tolkien"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    authors = [b["author"] for b in items]
    assert any("Tolkien" in a for a in authors), (
        f"Expected Tolkien book in results for q=tolkien, got authors: {authors}"
    )
    assert not any("Herbert" in a for a in authors)


async def test_search_returns_relevance_ranked(
    client: AsyncClient, admin_headers: dict
) -> None:
    """When q matches both title and author, title-weight (A) matches rank higher than author-weight (B)."""
    # "Ring" in title -> weight A (higher rank)
    await _create_book(
        client, admin_headers,
        title="Ring of Fire",
        author="Anonymous Author",
        price="10.00",
    )
    # "Ring" in author name -> weight B (lower rank)
    await _create_book(
        client, admin_headers,
        title="Completely Different Title",
        author="Ring Scholar",
        price="10.00",
    )

    resp = await client.get("/books", params={"q": "ring"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 2, "Both books should match 'ring'"
    # Title match ("Ring of Fire") should appear before author match ("Ring Scholar")
    titles = [b["title"] for b in items]
    assert "Ring of Fire" in titles
    assert "Completely Different Title" in titles
    assert titles.index("Ring of Fire") < titles.index("Completely Different Title"), (
        "Title-weight match should rank higher than author-weight match"
    )


async def test_search_no_results(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?q=xyzunmatchable returns empty items list with total=0."""
    await _create_book(client, admin_headers, title="Dune", author="Frank Herbert", price="15.99")

    resp = await client.get("/books", params={"q": "xyzunmatchable"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_search_special_chars_no_error(client: AsyncClient) -> None:
    """GET /books?q=C%2B%2B (C++) returns 200 without error -- special chars are stripped safely."""
    resp = await client.get("/books", params={"q": "C++"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # Result may be empty (no matching books) but must not be a server error
    assert isinstance(data["items"], list)


async def test_search_case_insensitive(client: AsyncClient, admin_headers: dict) -> None:
    """FTS search is case-insensitive: 'DUNE', 'dune', 'Dune' all match."""
    await _create_book(client, admin_headers, title="Dune", author="Frank Herbert", price="15.99")

    for query in ("DUNE", "dune", "Dune"):
        resp = await client.get("/books", params={"q": query})
        assert resp.status_code == 200
        items = resp.json()["items"]
        titles = [b["title"] for b in items]
        assert "Dune" in titles, f"Expected 'Dune' in results for q={query!r}, got: {titles}"


# ---------------------------------------------------------------------------
# DISC-03: Filtering by genre_id and author
# ---------------------------------------------------------------------------


async def test_filter_by_genre_id(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?genre_id={id} returns only books assigned to that genre."""
    genre = await _create_genre(client, admin_headers, "Science Fiction")
    genre_id = genre["id"]

    await _create_book(
        client, admin_headers,
        title="Foundation",
        author="Isaac Asimov",
        price="12.99",
        genre_id=genre_id,
    )
    await _create_book(
        client, admin_headers,
        title="Pride and Prejudice",
        author="Jane Austen",
        price="8.99",
        # no genre_id
    )

    resp = await client.get("/books", params={"genre_id": genre_id})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    for book in items:
        assert book["genre_id"] == genre_id, (
            f"Expected all results to have genre_id={genre_id}, got: {book['genre_id']}"
        )
    titles = [b["title"] for b in items]
    assert "Foundation" in titles
    assert "Pride and Prejudice" not in titles


async def test_filter_by_author(client: AsyncClient, admin_headers: dict) -> None:
    """GET /books?author=tolkien returns books with 'tolkien' in author name (case-insensitive)."""
    await _create_book(
        client, admin_headers,
        title="The Fellowship of the Ring",
        author="J.R.R. Tolkien",
        price="14.99",
    )
    await _create_book(
        client, admin_headers,
        title="The Two Towers",
        author="J.R.R. Tolkien",
        price="14.99",
    )
    await _create_book(
        client, admin_headers,
        title="Dune",
        author="Frank Herbert",
        price="15.99",
    )

    resp = await client.get("/books", params={"author": "tolkien"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    for book in items:
        assert "tolkien" in book["author"].lower(), (
            f"Expected 'tolkien' in author, got: {book['author']}"
        )
    titles = [b["title"] for b in items]
    assert "The Fellowship of the Ring" in titles
    assert "The Two Towers" in titles
    assert "Dune" not in titles


async def test_filter_combined_q_and_genre(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books?q=ring&genre_id={id} returns only books matching both conditions."""
    fantasy = await _create_genre(client, admin_headers, "Fantasy")
    scifi = await _create_genre(client, admin_headers, "Science Fiction")
    fantasy_id = fantasy["id"]
    scifi_id = scifi["id"]

    # Matches q=ring AND genre=fantasy
    await _create_book(
        client, admin_headers,
        title="The Fellowship of the Ring",
        author="J.R.R. Tolkien",
        price="14.99",
        genre_id=fantasy_id,
    )
    # Matches q=ring but wrong genre
    await _create_book(
        client, admin_headers,
        title="Ring World",
        author="Larry Niven",
        price="11.99",
        genre_id=scifi_id,
    )
    # Matches genre=fantasy but not q=ring
    await _create_book(
        client, admin_headers,
        title="The Hobbit",
        author="J.R.R. Tolkien",
        price="12.99",
        genre_id=fantasy_id,
    )

    resp = await client.get("/books", params={"q": "ring", "genre_id": fantasy_id})
    assert resp.status_code == 200
    items = resp.json()["items"]
    titles = [b["title"] for b in items]
    assert "The Fellowship of the Ring" in titles
    assert "Ring World" not in titles, "SciFi ring book should be excluded by genre filter"
    assert "The Hobbit" not in titles, "Non-ring book should be excluded by FTS filter"


async def test_filter_no_match_returns_empty(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books?genre_id=99999 returns empty items for a non-existent genre."""
    await _create_book(client, admin_headers, title="Some Book", author="Some Author", price="9.99")

    resp = await client.get("/books", params={"genre_id": 99999})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# DISC-04: Book detail with in_stock boolean
# ---------------------------------------------------------------------------


async def test_get_book_detail_in_stock(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books/{id} for a book with stock_quantity=5 returns in_stock=true."""
    book = await _create_book(
        client, admin_headers,
        title="Dune",
        author="Frank Herbert",
        price="15.99",
    )
    await _set_stock(client, admin_headers, book["id"], quantity=5)

    resp = await client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock_quantity"] == 5
    assert data["in_stock"] is True


async def test_get_book_detail_out_of_stock(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books/{id} for a book with stock_quantity=0 returns in_stock=false."""
    book = await _create_book(
        client, admin_headers,
        title="The Fellowship of the Ring",
        author="J.R.R. Tolkien",
        price="14.99",
    )
    # stock defaults to 0 on creation -- no PATCH needed

    resp = await client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock_quantity"] == 0
    assert data["in_stock"] is False


async def test_get_book_detail_full_fields(
    client: AsyncClient, admin_headers: dict
) -> None:
    """GET /books/{id} response includes all expected fields including in_stock."""
    genre = await _create_genre(client, admin_headers, "Classic Fiction")
    book = await _create_book(
        client, admin_headers,
        title="To Kill a Mockingbird",
        author="Harper Lee",
        price="11.99",
        isbn="9780061935466",
        genre_id=genre["id"],
        description="A novel about racial injustice.",
        cover_image_url="https://example.com/mockingbird.jpg",
        publish_date="1960-07-11",
    )
    await _set_stock(client, admin_headers, book["id"], quantity=10)

    resp = await client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == book["id"]
    assert data["title"] == "To Kill a Mockingbird"
    assert data["author"] == "Harper Lee"
    assert float(data["price"]) == 11.99
    assert data["isbn"] == "9780061935466"
    assert data["genre_id"] == genre["id"]
    assert data["description"] == "A novel about racial injustice."
    assert data["cover_image_url"] == "https://example.com/mockingbird.jpg"
    assert data["publish_date"] == "1960-07-11"
    assert data["stock_quantity"] == 10
    assert data["in_stock"] is True


async def test_get_book_detail_not_found(client: AsyncClient) -> None:
    """GET /books/99999 for an unknown book ID returns 404 with BOOK_NOT_FOUND code."""
    resp = await client.get("/books/99999")
    assert resp.status_code == 404
    assert resp.json()["code"] == "BOOK_NOT_FOUND"


async def test_get_book_detail_stock_boundary(
    client: AsyncClient, admin_headers: dict
) -> None:
    """in_stock transitions correctly at the stock_quantity=0 boundary."""
    book = await _create_book(
        client, admin_headers,
        title="Boundary Book",
        author="Author B",
        price="9.99",
    )
    # Start at 0 -- out of stock
    resp = await client.get(f"/books/{book['id']}")
    assert resp.json()["in_stock"] is False

    # Set to 1 -- now in stock
    await _set_stock(client, admin_headers, book["id"], quantity=1)
    resp = await client.get(f"/books/{book['id']}")
    assert resp.json()["in_stock"] is True

    # Back to 0 -- out of stock again
    await _set_stock(client, admin_headers, book["id"], quantity=0)
    resp = await client.get(f"/books/{book['id']}")
    assert resp.json()["in_stock"] is False
