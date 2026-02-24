# BookStore

## What This Is

An online bookstore application where administrators manage a catalog of books (with details, pricing, and stock) and users can browse, search, purchase books through a cart/checkout flow, maintain wishlists, and pre-book upcoming or out-of-stock titles. Built with FastAPI, PostgreSQL, SQLAlchemy, and managed with Poetry.

## Core Value

Users can discover and purchase books from a well-managed catalog with a smooth cart-to-checkout experience.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Admin can add, edit, and delete books with full details (title, author, price, ISBN, genre, description, cover image URL, publish date)
- [ ] Admin can manage book stock quantities
- [ ] Users can sign up, log in, and authenticate via JWT tokens
- [ ] Users can browse and search/filter books by title, author, or genre
- [ ] Users can add books to a shopping cart and go through checkout (mock payment)
- [ ] Users can view their order history
- [ ] Users can add/remove books from a personal wishlist
- [ ] Users can pre-book (reserve) upcoming or out-of-stock books and get notified when available
- [ ] Books have tracked stock quantities with out-of-stock state
- [ ] Role-based access: admin manages catalog, users shop

### Out of Scope

- Real payment integration (Stripe, etc.) — mock payment is sufficient for v1
- Mobile app — API-first, web/API only
- Email delivery system — notifications tracked in-app only for v1
- Social features (reviews, ratings) — keep v1 focused on core commerce
- Multiple storefronts or multi-tenant — single bookstore

## Context

- Greenfield project, no existing code
- FastAPI chosen as the web framework (async, modern Python)
- Poetry for dependency management and packaging
- PostgreSQL as the database with SQLAlchemy ORM and Alembic for migrations
- JWT-based stateless authentication with access/refresh tokens
- Two user roles: admin (catalog management) and regular user (shopping)
- Cart + checkout flow with simulated/mock payment processing
- Pre-booking is a reservation system — users express interest in unavailable books, tracked for fulfillment when stock arrives

## Constraints

- **Stack**: Python 3.11+, FastAPI, Poetry, PostgreSQL, SQLAlchemy + Alembic
- **Auth**: JWT tokens (access + refresh)
- **Payments**: Mock/simulated only — no real payment gateway

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Django/Flask | Async-native, automatic OpenAPI docs, modern Python patterns | — Pending |
| PostgreSQL over SQLite | Production-grade, supports concurrent access, full-text search potential | — Pending |
| SQLAlchemy + Alembic | Industry standard ORM with robust migration support | — Pending |
| JWT over sessions | Stateless auth, scales better for API-first architecture | — Pending |
| Mock payments | Reduces complexity for v1, real integration deferred | — Pending |

---
*Last updated: 2026-02-25 after initialization*
