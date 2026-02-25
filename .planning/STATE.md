# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** Phase 5 - Discovery (up next)

## Current Position

Phase: 4 of 9 (Catalog) -- COMPLETE
Plan: 3 of 3 in current phase (plans 01-03 done)
Status: Phase complete — advancing to Phase 5
Last activity: 2026-02-25 — Plan 04-03 complete (22 catalog integration tests covering CATL-01 through CATL-05)

Progress: [███████░░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: ~3 min
- Total execution time: ~0.6 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 Infrastructure | 4/4 | 15 min | 3.75 min |
| Phase 02 Core Auth | 5/5 | ~13 min | ~2.5 min |
| Phase 03 OAuth | 3/3 | ~15 min | ~5 min |
| Phase 04 Catalog | 3/3 | ~25 min | ~8 min |

**Recent Trend:**
- Last 5 plans: 03-03 (5 min), 04-01 (10 min), 04-02 (5 min), 04-03 (10 min)
- Trend: Stable

*Updated after each plan completion*

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 5]: PostgreSQL full-text search configuration (generated tsvector column vs. on-the-fly computation) must be decided before Phase 5 migrations are written
- [Phase 7]: Multi-item checkout deadlock prevention pattern (ascending ID lock order vs. SKIP LOCKED with retry) should be confirmed during Phase 7 planning
- [Phase 9]: Stock update to pre-booking notification coupling placement (BookService calling PreBookRepository directly vs. domain events) must be decided before Phase 9 to avoid circular imports

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 04-03-PLAN.md (Phase 4 Catalog plan 03: 22 catalog integration tests complete; Phase 4 fully done -- ready for Phase 5 Discovery)
