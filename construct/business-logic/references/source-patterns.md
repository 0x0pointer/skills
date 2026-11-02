# Business-logic source patterns

What enforcement looks like in code, and what its absence looks like, per invariant family.
The question each time: **is the rule enforced on the server, on every path, in a way the client
cannot influence?**

## 1. Ownership and tenancy (idor)

Unscoped load followed by use:
```python
order = Order.objects.get(pk=order_id)               # Django
order = Order.query.get_or_404(order_id)             # Flask-SQLAlchemy
```
```js
const order = await Order.findById(req.params.id);   // Mongoose
```
```java
Order order = orderRepository.findById(id).orElseThrow();
```
Scoped load (enforced):
```python
order = Order.objects.get(pk=order_id, user=request.user)
order = request.user.orders.get(pk=order_id)
```
```java
Order order = orderRepository.findByIdAndOwnerId(id, principal.getId()).orElseThrow();
```
Also enforced: an explicit check right after the load (`if order.user_id != current_user.id:
abort(404)`), a policy call (`authorize('update', order)`), a DRF `get_queryset()` filtered by
the user combined with `get_object()`, or a row-level security policy in the DB.

Tenancy tells: a base repository or query scope that adds `tenant_id` automatically (Django
manager, Hibernate filter, EF global query filter, Laravel global scope). New code that bypasses
it (`objects.unscoped`, `IgnoreQueryFilters()`, `withoutGlobalScopes()`, raw SQL) is a candidate.
Tenant id taken from the **request** (`body.tenant_id`, `X-Tenant-Id` header) instead of the
authenticated principal is a candidate.

Negative ownership: request fields naming the *actor* (`from_account_id`, `sender_id`,
`created_by`, `payer_id`) accepted from the client instead of derived from the session.

## 2. Role and function (bfla)

- New admin-ish handler (`approve`, `refund`, `export`, `impersonate`, `set_role`, `delete_user`)
  without a role decorator / policy / guard, when siblings have one.
- Role checks that compare client-supplied claims (`body.role`, unverified JWT payload).
- Permission checks inverted or short-circuited (`if not user.is_admin and not DEBUG`).
- Fail-open: exceptions in the check swallowed (`except Exception: pass`), `next()` called in an
  auth middleware's error path, feature-flag / entitlement lookups that default to `true`.

## 3. Writable fields (mass-assignment)

- Whole request body bound to a persistent model: `Model(**data)`, `Model.create(req.body)`,
  `fill($request->all())`, `@RequestBody Entity`, `[FromBody] Entity`, `ModelSerializer` with
  `fields = "__all__"`.
- Fields that matter: `role`, `is_admin`, `permissions`, `status`, `state`, `verified`,
  `email_verified`, `price`, `amount`, `balance`, `credits`, `plan`, `tenant_id`, `owner_id`,
  `user_id`, `created_by`, `approved_by`.
- Enforced: explicit allowlists (`$fillable`, `read_only_fields`, DTO with only writable fields,
  `pick(...)`), or the sensitive field overwritten from server state after binding.

## 4. State machines and step order (workflow-bypass)

Unenforced:
```python
order.status = request.json["status"]; order.save()
```
```js
await Order.updateOne({ _id: id }, req.body);    // body may carry status
```
```java
order.setStatus(request.getStatus()); repo.save(order);
```
Enforced: a transition table or state-machine library (`django-fsm`, `transitions`, `xstate`,
Spring State Machine, `aasm`) or an explicit guard `if order.status != "paid": raise`. Check
that **every** endpoint that changes the state uses it; new endpoints often set the field
directly.

Step order: a later step (`confirm`, `ship`, `activate`, `complete_signup`) must check a
server-side marker set by the earlier step (`payment_captured_at`, `email_verified`), not a
client-supplied flag (`"paid": true`) or the mere existence of a session.

One-time tokens: after use, is the token deleted / marked used **in the same transaction** as
the effect? Is expiry checked against a stored timestamp?

## 5. Values, quantities, limits (value-tampering)

- Prices, totals, discounts or fees taken from the request instead of computed from server data.
- Quantity / amount fields with no lower bound (`>= 1` / `> 0`) or upper bound; signed integer
  types for quantities; Pydantic `int` without `gt=0`; JSON schema without `minimum`.
- Arithmetic in floats for money; rounding per line item in the customer's favour; integer
  overflow in fixed-width types (Java `int`, Go `int32`, DB `INTEGER` columns).
- Limits checked against a client-supplied count, or checked on create but not on update/import.
- Currency or unit taken from the client with no conversion.

## 6. Atomicity and idempotency (race-condition)

Racy read-modify-write:
```python
acct = Account.objects.get(pk=pk)
if acct.balance >= amount:
    acct.balance -= amount
    acct.save()
```
Enforced: single conditional update (`UPDATE ... SET balance = balance - :a WHERE id = :id AND
balance >= :a` and checking rows affected), `select_for_update()` / `FOR UPDATE` inside a
transaction, optimistic locking (`@Version`, `lock_version`) with the conflict handled, atomic
counters (`$inc` with filter guard, Redis `DECRBY` / Lua), unique constraints on idempotency keys
or `(user_id, voucher_id)`.

Check-then-act on quotas: `if count(...) < limit: create(...)` in two statements.

Idempotency: webhook / payment / message handlers must dedupe by an event or idempotency id
stored with a unique constraint **before** or atomically with the side effect.

## 7. Time (workflow-bypass)

- Expiry / validity compared against a value from the current request (`body.valid_until`).
- Server time from client headers. Time zone confusion in comparisons (naive vs aware).
- Promotion windows checked at cart time but not at payment time.

## 8. Data exposure

- Serialising whole models (`to_dict()`, `model_dump()`, default Jackson, `res.json(user)`)
  into responses: password hashes, tokens, internal flags, other users' PII.
- List endpoints returning more than the caller's own rows (missing filter, see section 1).
- Error messages or debug fields revealing internals.
