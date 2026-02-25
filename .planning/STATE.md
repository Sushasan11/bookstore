# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.
**Current focus:** Phase 4 - Catalog (next)

## Current Position

Phase: 3 of 9 (OAuth) -- COMPLETE
Plan: 3 of 3 in current phase (all done)
Status: Phase complete
Last activity: 2026-02-25 — Plan 03-03 complete (OAuth integration tests created)

Progress: [████░░░░░░] 33%

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: ~3 min
- Total execution time: ~0.6 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 Infrastructure | 4/4 | 15 min | 3.75 min |
| Phase 02 Core Auth | 5/5 | ~13 min | ~2.5 min |
| Phase 03 OAuth | 3/3 | ~15 min | ~5 min |

**Recent Trend:**
- Last 5 plans: 02-04 (3 min), 02-05 (3 min), 03-01 (5 min), 03-02 (5 min), 03-03 (5 min)
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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 5]: PostgreSQL full-text search configuration (generated tsvector column vs. on-the-fly computation) must be decided before Phase 5 migrations are written
- [Phase 7]: Multi-item checkout deadlock prevention pattern (ascending ID lock order vs. SKIP LOCKED with retry) should be confirmed during Phase 7 planning
- [Phase 9]: Stock update to pre-booking notification coupling placement (BookService calling PreBookRepository directly vs. domain events) must be decided before Phase 9 to avoid circular imports

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 03-03-PLAN.md (Phase 3 OAuth fully complete; ready for Phase 4 Catalog)
