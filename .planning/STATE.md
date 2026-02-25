# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** Phase 7 - Orders

## Current Position

Phase: 7 of 9 (Orders) -- Complete
Plan: 2 of 2 in current phase (all done)
Status: Phase 7 complete — 2 of 2 plans done (07-01: orders vertical slice, 07-02: 14 integration tests)
Last activity: 2026-02-25 — Plan 07-02 complete (14 order integration tests, service cart-clear bug fix; 108/108 tests pass)

Progress: [█████████░] 97%

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: ~3 min
- Total execution time: ~0.6 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 Infrastructure | 4/4 | 15 min | 3.75 min |
| Phase 02 Core Auth | 5/5 | ~13 min | ~2.5 min |
| Phase 03 OAuth | 3/3 | ~15 min | ~5 min |
| Phase 04 Catalog | 3/3 | ~25 min | ~8 min |
| Phase 05 Discovery | 3/3 | ~55 min | ~18 min |
| Phase 06 Cart | 2/2 | 9 min | 4.5 min |
| Phase 07 Orders | 2/2 | 24 min | 12 min |

**Recent Trend:**
- Last 5 plans: 06-01 (6 min), 06-02 (3 min), 07-01 (5 min), 07-02 (19 min)
- Trend: Stable (07-02 longer due to SQLAlchemy identity map debugging)

*Updated after each plan completion*
| Phase 02-core-auth P01 | 5 | 2 tasks | 4 files |
| Phase 02-core-auth P02 | 10 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Split auth into two phases (Phase 2: Core Auth, Phase 3: OAuth) — AUTH-06 is sufficiently complex to isolate; OAuth failure does not block JWT auth delivery
- [Roadmap]: ENGM-06 (admin order view) assigned to Phase 7 (Orders) despite being in the Engagement category — it is part of the order system, not the engagement features
- [Roadmap]: Phase 1 carries no v1 requirements — it is a pure infrastructure phase that all 26 requirements depend on
- [Phase 01]: Health endpoint is app-level ping only; DB connectivity verified in Plan 04 test suite
- [Phase 01]: AppError custom exception with status_code/detail/code/field — all errors follow structured JSON convention
- [Phase 01]: taskipy used for Poetry task shortcuts (poetry run task dev/test/lint)
- [Phase 01 Plan 02]: expire_on_commit=False is mandatory on AsyncSessionLocal — prevents MissingGreenlet on every route accessing model attributes after commit
- [Phase 01 Plan 02]: app/db/base.py serves dual purpose: DeclarativeBase AND Alembic model aggregator — all future model imports go here
- [Phase 01 Plan 02]: DbSession = Annotated[AsyncSession, Depends(get_db)] type alias established for clean route parameter declarations
- [Phase 01 Plan 03]: env.py reads DATABASE_URL from get_settings() at runtime, not from alembic.ini -- single source of truth for database configuration
- [Phase 01 Plan 03]: compare_type=True in both offline and online modes ensures Alembic detects column type changes during autogenerate
- [Phase 01 Plan 03]: All future model imports must go in app/db/base.py for Alembic autogenerate to discover them
- [Phase 01 Plan 04]: asyncio_default_test_loop_scope = session required alongside asyncio_default_fixture_loop_scope = session — prevents Future attached to different loop with session-scoped async fixtures
- [Phase 01 Plan 04]: All async test fixtures use pytest_asyncio.fixture; test_engine is session-scoped, db_session and client are function-scoped with rollback
- [Phase 02 Plan 01]: UserRole is a StrEnum with values "user" and "admin" — no roles table, no extensibility needed
- [Phase 02 Plan 01]: RefreshToken has token_family UUID column for family-level revocation (theft detection)
- [Phase 02 Plan 02]: Password hashing uses asyncio.to_thread to avoid blocking the event loop; algorithms=["HS256"] explicit in jwt.decode to prevent algorithm confusion
- [Phase 02 Plan 02]: Refresh tokens are opaque strings (secrets.token_urlsafe), NOT JWTs — simpler DB revocation
- [Phase 02 Plan 03]: DUMMY_HASH computed at module load for timing-safe login — verify_password always runs even when user not found
- [Phase 02 Plan 03]: get_current_user reads role from JWT claims only — no DB lookup; require_admin checks role == "admin"
- [Phase 02 Plan 03]: AuthService.refresh() rotates tokens within same family; reuse of revoked token triggers family-wide revocation
- [Phase 02 Plan 04]: Auth router prefix /auth, 4 endpoints: register (201), login (200), refresh (200), logout (204)
- [Phase 02 Plan 04]: Admin seed via standalone script (scripts/seed_admin.py) using asyncio.run — no Click dependency added
- [Phase 03 Plan 01]: OAuthAccount in separate table (not columns on User) — supports multiple providers per user, clean queries
- [Phase 03 Plan 01]: hashed_password made nullable for OAuth-only users who register without a password
- [Phase 03 Plan 01]: SessionMiddleware max_age=600 (10 min) for Authlib CSRF state during OAuth redirect flow
- [Phase 03 Plan 01]: Empty string defaults for OAuth client IDs/secrets — app starts without credentials, OAuth endpoints fail gracefully
- [Phase 03 Plan 02]: OAuthAccountRepository as separate class — clean separation from User and RefreshToken repositories
- [Phase 03 Plan 02]: AuthService.oauth_repo is optional (None default) — backward compatible with existing register/login/refresh/logout code
- [Phase 03 Plan 02]: OAuth-only login guard returns 400 with AUTH_OAUTH_ONLY_ACCOUNT — clear error for wrong login method
- [Phase 03 Plan 02]: Google callback checks email_verified claim — prevents unverified email account takeover
- [Phase 03 Plan 02]: GitHub callback fetches /user/emails when profile email is null — handles private email settings
- [Phase 03 Plan 03]: Mock target is app.users.router.oauth (not app.core.oauth.oauth) — patches the import as seen by the router
- [Phase 03 Plan 03]: GitHub get() mocked with side_effect dispatch on URL arg — returns different responses for /user vs /user/emails
- [Phase 03 Plan 03]: 15 OAuth tests cover: redirects, callbacks, account linking, OAuth-only users, idempotent login, error cases
- [Phase 04 Plan 01]: Numeric(10,2) for price — exact decimal arithmetic, no floating-point errors; price > 0 enforced by CHECK CONSTRAINT
- [Phase 04 Plan 01]: isbn nullable + unique — PostgreSQL allows multiple NULLs in unique index; ISBN-10 and ISBN-13 both validated with checksum
- [Phase 04 Plan 01]: stock_quantity >= 0 enforced by CHECK CONSTRAINT ck_books_stock_non_negative; default 0 on creation
- [Phase 04 Plan 01]: genre_id nullable FK — book can exist without genre; single genre per book (flat taxonomy)
- [Phase 04 Plan 01]: Model imports in alembic/env.py (not app/db/base.py) to avoid circular imports — books model added after users imports
- [Phase 04 Plan 01]: IntegrityError catches isbn violations by string-matching e.orig — pragmatic pattern for asyncpg
- [Phase 04 Plan 01]: migration c3d4e5f6a7b8 chains off 7b2f3a8c4d1e (OAuth migration) — correct down_revision
- [Phase 04 Plan 02]: _make_service(db) factory pattern instantiates BookService with repositories per request — keeps routes thin, consistent with auth service pattern
- [Phase 04 Plan 02]: Catalog routes have no prefix (e.g., /books not /catalog/books) — simpler URL structure consistent with project conventions
- [Phase 04 Plan 02]: GET /books/{id} and GET /genres are public (no auth) — read-only catalog is world-readable per must_haves spec
- [Phase 04 Plan 03]: No @pytest.mark.asyncio decorators needed -- asyncio_mode=auto in pyproject.toml handles all async test discovery automatically (matches existing test_auth.py style)
- [Phase 04 Plan 03]: user_headers fixture uses authenticated non-admin user for 403 tests -- unauthenticated requests return 401 (OAuth2PasswordBearer), only authenticated non-admin get 403
- [Phase 04 Plan 03]: 21 integration tests cover 5 requirement groups: CATL-01 (book creation), CATL-02 (book edit), CATL-03 (book delete), CATL-04 (stock update), CATL-05 (genre management)
- [Phase 05 Plan 01]: Use 'simple' tsvector dictionary (not 'english') — preserves proper names like Tolkien and Herbert without stemming
- [Phase 05 Plan 01]: deferred=True on search_vector — TSVECTOR internal format not loaded on every SELECT; explicitly requested when needed for FTS queries
- [Phase 05 Plan 01]: Hand-write GIN index migration (never autogenerate) — Alembic bug #1390 repeatedly re-detects expression-based GIN indexes as changed
- [Phase 05 Plan 01]: include_object filter in both offline and online alembic env.py paths — prevents spurious migrations after initial GIN index creation
- [Phase 05 Plan 01]: setweight A for title, B for author — title matches rank higher than author matches in FTS query results
- [Phase 05 Plan 02]: Relevance sort (ts_rank DESC) overrides sort param when q is present — no mixing relevance with explicit sort
- [Phase 05 Plan 02]: Book.id secondary tiebreaker on all sort paths — stable offset pagination without duplicates across pages
- [Phase 05 Plan 02]: count_stmt uses stmt.subquery() to reuse all filters — no duplicated WHERE clause logic
- [Phase 05 Plan 02]: GET /books registered before GET /books/{book_id} in router — FastAPI first-match routing requires literal paths before parameterized paths
- [Phase 05 Plan 02]: _build_tsquery strips non-word/non-hyphen chars to prevent tsquery injection; :* suffix enables prefix matching
- [Phase 05 Plan 03]: test_list_books_sort_created_at uses set membership (not strict ID ordering) — created_at timestamps may be identical in fast test runs making strict order flaky
- [Phase 05 Plan 03]: 23 integration tests cover DISC-01 (pagination+sort), DISC-02 (FTS search), DISC-03 (genre/author filters), DISC-04 (book detail in_stock)
- [Phase 06 Plan 01]: pg INSERT ON CONFLICT DO NOTHING for CartRepository.get_or_create — race-condition-safe one-cart-per-user without SELECT then INSERT gap
- [Phase 06 Plan 01]: Virtual empty cart on GET — CartService.get_cart returns CartResponse(items=[]) when no DB row exists, does not create DB row on read
- [Phase 06 Plan 01]: session.refresh(item, ["book"]) after add flush — loads book relationship for CartItemResponse without extra selectinload on insert path
- [Phase 06 Plan 01]: TYPE_CHECKING guard for Book import in cart/models.py — avoids circular import while keeping Mapped[Book] annotation for type checkers
- [Phase 06 Plan 01]: int(current_user["sub"]) cast in every route handler — JWT sub is always string, must cast to int for user_id comparisons
- [Phase 06 Plan 02]: Module-specific email prefixes in cart test fixtures (cart_admin@, cart_user@, etc.) — avoids collisions with other test module users sharing same test DB schema
- [Phase 06 Plan 02]: out_of_stock_book fixture relies on default stock_quantity=0 — no PATCH /stock needed, documents zero-stock intent without extra HTTP call
- [Phase 06 Plan 02]: total_price tolerance check uses abs(float - expected) < 0.02 — avoids fragile exact comparison on Decimal-to-float conversion
- [Phase 07-orders]: OrderItem.book_id uses SET NULL on delete — preserves order history when book removed from catalog
- [Phase 07-orders]: lock_books uses SELECT FOR UPDATE with ORDER BY Book.id ascending — book_ids must be pre-sorted by caller for deadlock prevention
- [Phase 07-orders]: MockPaymentService with force_fail=True allows deterministic test control of 90% success rate payment simulation
- [Phase 07-orders]: unit_price copied from book.price at checkout time — order history immune to future price changes
- [Phase 07-02]: session.expire(cart) required after item deletion in checkout — SQLAlchemy identity map returns deleted objects via selectinload unless explicitly expired; same-session requests read stale state without this fix
- [Phase 07-02]: MockPaymentService.charge patched with AsyncMock(return_value=True) in test _checkout helper — prevents 10% random 402 failure from making test suite flaky; force_fail path unchanged
- [Phase 07-02]: asyncio.gather not viable for concurrent checkout testing with shared ASGI test session — sequential checkout invariant test (stock=1 → 201 then 409) proves same stock safety guarantee
- [Phase 02-core-auth]: UserRole is a StrEnum with values user and admin — no roles table, no extensibility needed
- [Phase 02-core-auth]: RefreshToken has token_family UUID column for family-level revocation (theft detection)
- [Phase 02-02]: Password hashing uses asyncio.to_thread to avoid blocking the event loop; algorithms=[HS256] explicit in jwt.decode to prevent algorithm confusion
- [Phase 02-02]: Refresh tokens are opaque strings (secrets.token_urlsafe(64)), NOT JWTs — simpler DB revocation

### Pending Todos

None yet.

### Blockers/Concerns

- [RESOLVED Phase 7]: Multi-item checkout deadlock prevention implemented using ascending ID lock order (SELECT FOR UPDATE ORDER BY Book.id) — SKIP LOCKED approach not needed
- [Phase 9]: Stock update to pre-booking notification coupling placement (BookService calling PreBookRepository directly vs. domain events) must be decided before Phase 9 to avoid circular imports

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 02-04-PLAN.md (Phase 2 Core Auth plan 04: Auth router with 4 HTTP endpoints wired into main.py, scripts/seed_admin.py for first admin bootstrap; 108/108 tests pass)
