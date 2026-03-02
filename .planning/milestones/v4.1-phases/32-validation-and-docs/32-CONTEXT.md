# Phase 32: Validation and Docs - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm email improvements (logo CID embedding, Open Library cover fallback) work end-to-end in a real SMTP environment, fix the restock alert template to display book cover images, correct SUMMARY frontmatter in three plans, and regenerate api.generated.ts to include the period query param for top-books.

</domain>

<decisions>
## Implementation Decisions

### Email verification method
- Use a local SMTP trap tool (MailHog or similar) — no real credentials needed
- Create a Python test script (e.g., `backend/scripts/test_email.py`) that sends sample order confirmation and restock alert emails
- Visual inspection of rendered emails in the SMTP trap web UI is sufficient — no screenshot artifacts needed
- Keep the test script in the repo as a developer tool for future email template changes

### Restock alert book cover
- Add a book cover image to `restock_alert.html`, centered above the book title inside the existing book card
- Medium hero-style size (~120x170px) since this is a single-book spotlight email
- Use the same 3-step fallback chain as `order_confirmation.html`: 1st cover_image_url (local), 2nd Open Library by ISBN, 3rd book emoji placeholder
- Backend caller must be updated to pass `isbn` and `cover_image_url` to the restock alert template context (currently only passes `book_title` and `store_url`)

### SUMMARY frontmatter corrections
- Fix all three plans: 26-02, 27-01, AND 31-02 (covers DOCS-01 scope plus the audit-identified ANLY-01 gap in 31-02)
- Claude determines correct requirement IDs from git history, SUMMARY content, and the milestone audit cross-reference
- SUMMARY files are in archived milestone directories (`milestones/v3.1-phases/`) for 26-02 and 27-01, and in active phases for 31-02

### API type regeneration
- One-time regeneration of `frontend/src/types/api.generated.ts` from backend OpenAPI spec
- Must include the `period` query param on the top-books endpoint
- No new npm script needed — just run the openapi-typescript command once

### Claude's Discretion
- Choice of local SMTP trap tool (MailHog, maildev, etc.)
- Exact test script structure and sample data
- How to run the backend OpenAPI spec extraction for type regeneration
- Styling details of the cover image in restock alert (border-radius, shadow, etc.)

</decisions>

<specifics>
## Specific Ideas

- Restock alert cover should feel like a "spotlight" — larger than order confirmation thumbnails since it's about a single book
- Test script should be repeatable — useful for any future email template changes
- The order_confirmation.html cover image pattern is the reference implementation to follow

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/email/service.py`: EmailService with `enqueue()` method, Jinja2 rendering, multipart/related MIME, CID logo embedding
- `backend/app/email/templates/base.html`: Base template with header (CID logo), content block, footer
- `backend/app/email/templates/order_confirmation.html`: Reference for cover image fallback chain (cover_image_url → Open Library ISBN → emoji placeholder)
- `backend/app/email/static/logo-white.png`: Logo file for CID embedding

### Established Patterns
- Email templates use Jinja2 inheritance (`{% extends "base.html" %}`)
- Cover images use direct `<img>` tags with Open Library URL pattern: `https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg`
- SUMMARY frontmatter uses YAML with fields like `phase`, `plan`, `subsystem`, `tags`, `dependency_graph`, `tech_stack`, `key_files`
- `api.generated.ts` is produced by `openapi-typescript` from the backend OpenAPI JSON spec

### Integration Points
- Restock alert emails are triggered from `backend/app/books/router.py` (stock update triggers notification to pre-booking users)
- SUMMARY files: `26-02` at `.planning/milestones/v3.1-phases/26-admin-foundation/26-02-SUMMARY.md`, `27-01` at `.planning/milestones/v3.1-phases/27-sales-analytics-and-inventory-alerts/27-01-SUMMARY.md`, `31-02` at `.planning/phases/31-code-quality/31-02-SUMMARY.md`
- `api.generated.ts` at `frontend/src/types/api.generated.ts` — generated from backend at `http://localhost:8000/openapi.json`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-validation-and-docs*
*Context gathered: 2026-03-02*
