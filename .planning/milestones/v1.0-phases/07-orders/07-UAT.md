---
status: complete
phase: 07-orders
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md
started: 2026-02-25T17:30:00Z
updated: 2026-02-25T17:40:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Checkout creates order and decrements stock
expected: POST /orders/checkout with a valid cart returns 201 with order details (order ID, status CONFIRMED, items with unit_price). The book's stock_quantity decreases by the purchased quantity. The cart is emptied after successful checkout.
result: pass

### 2. Checkout on empty cart returns error
expected: POST /orders/checkout with an empty cart returns 400 error (CART_EMPTY or similar). No order is created.
result: pass

### 3. Checkout with insufficient stock returns error
expected: POST /orders/checkout when cart quantity exceeds available stock returns 409 (ORDER_INSUFFICIENT_STOCK) with details about which book(s) lack stock. Cart is preserved (not cleared).
result: pass

### 4. Payment failure preserves cart
expected: When payment fails (force_fail=True), POST /orders/checkout returns 402 (PAYMENT_FAILED). The cart still contains all its items — nothing is lost.
result: pass

### 5. Unit price snapshot captures checkout-time price
expected: If a book's price changes after being added to cart, the order's unit_price reflects the price at checkout time, not the price when the item was added to cart.
result: pass

### 6. User order history lists own orders only
expected: GET /orders returns a list of orders belonging to the authenticated user. Orders from other users are not visible.
result: pass

### 7. Order detail shows items and total
expected: GET /orders/{id} returns the full order with items (book info, quantity, unit_price) and a computed total_price. Requesting another user's order returns 404.
result: pass

### 8. Admin can view all orders
expected: GET /admin/orders (with admin credentials) returns orders from all users. Non-admin users receive 403.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
