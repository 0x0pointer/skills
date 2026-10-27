# Triage examples

Each example shows the essence of the diff, the decision and the reasoning that justifies it.

## skip

**Button colour and spacing**
```diff
-  .btn-primary { background: #0055aa; padding: 4px 8px; }
+  .btn-primary { background: #0066cc; padding: 6px 10px; }
```
`skip` — styling only; no data binding, no script, no URL handling.

**Test-only change**
```diff
+def test_refund_rejects_other_users_order(client, other_user_order): ...
```
`skip` — only files under `tests/` change; production behaviour is untouched. (A test that is
*deleted* together with a production change is a different story: judge the production change.)

**Log wording**
```diff
-    logger.info("order %s created", order.id)
+    logger.info("created order id=%s", order.id)
```
`skip` — message text only; no new data is logged. If the new line logged a token, password,
card number or full request body it would be `light` with tag `data-exposure`.

## light

**New read-only endpoint over public data**
```diff
+@router.get("/api/countries")
+def list_countries():
+    return [c.dict() for c in COUNTRIES]
```
`light` — new reachable route, static non-sensitive data, no parameters. Tags: none or `area:api`.

**Validation tightened**
```diff
-    if len(name) > 200:
+    if len(name) > 100 or not NAME_RE.match(name):
```
`light` — makes a check stricter; worth a quick look that nothing else relied on the old shape.

**Query refactor with same bindings**
```diff
-    cur.execute("SELECT * FROM items WHERE id = %s", (item_id,))
+    cur.execute("SELECT id, name, price FROM items WHERE id = %s", (item_id,))
```
`light` — still parameterised; column list narrowed. Tag `sqli` is not warranted.

## full

**New search endpoint with string-built SQL**
```diff
+@app.get("/api/orders/search")
+def search():
+    q = request.args.get("q", "")
+    rows = db.execute(f"SELECT * FROM orders WHERE note LIKE '%{q}%'").fetchall()
```
`full` — new attacker-reachable route, request parameter interpolated into SQL. Tags: `sqli`.

**Ownership filter removed in a "simplification"**
```diff
-    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
+    order = Order.query.get_or_404(order_id)
```
`full` — the PR says "simplify lookup", but the `user_id` filter is gone. Tags: `idor`.

**Discount arithmetic**
```diff
+    total = sum(i.price * i.quantity for i in cart.items) - payload["discount"]
```
`full` — client-supplied value subtracted from a server total; quantity may be negative.
Tags: `value-tampering`, `business_logic:checkout`. Flows: `checkout`.

**New state transition**
```diff
+    if action == "approve":
+        invoice.status = "approved"
```
`full` — a state change with no visible check of the current state or of the approver's role.
Tags: `workflow-bypass`, `bfla`. Flows: `invoice-approval`.

**Shared middleware touched**
```diff
-    if not token or not verify(token):
+    if token and not verify(token):
         raise Unauthorized()
```
`full` — two characters change in the auth middleware: a request with no token now passes.
Tags: `authn-session`.

**Frontend raw HTML**
```diff
+  <div dangerouslySetInnerHTML={{ __html: comment.body }} />
```
`full` — renders user-authored content as HTML. Tags: `xss`.
