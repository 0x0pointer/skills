# Business Logic Source Patterns Reference

Lazy-loaded reference for Phase 5d of the `/codebase` skill. What to actually grep for, per language/framework, to find business-logic and workflow-integrity weaknesses from source alone — no live requests. Each section maps to a phase in the live-testing `/business-logic` skill for cross-reference, but the evidence here is a `file:line` trace, not an HTTP response.

---

## 1. State-machine / step-order enforcement

Maps to `/business-logic` Phase 2 (Workflow Bypass) and Phase 3 (State Machine Abuse).

**The question:** is a legal transition table enforced somewhere the client can't reach, or is the "state" just a column any authenticated write can set?

### Ruby / Rails

Guarded — real state-machine gem with transition constraints:
```ruby
# aasm
class Order
  include AASM
  aasm column: :status do
    state :pending, initial: true
    state :paid, :shipped, :refunded
    event :pay do
      transitions from: :pending, to: :paid, guard: :payment_verified?
    end
    event :refund do
      transitions from: [:paid, :shipped], to: :refunded, guard: :within_refund_window?
    end
  end
end
order.pay!  # raises AASM::InvalidTransition if guard fails or state doesn't allow it

# state_machines gem — same shape
state_machine :status, initial: :pending do
  event :ship do
    transition paid: :shipped
  end
end
```
Unguarded — plain column, mass-assignable:
```ruby
# Controller sets status directly from params — no transition table, no guard
def update
  @order.update(status: params[:status])   # any string the client sends
end

# Or worse: status included in strong params without a whitelist of allowed *values*
params.require(:order).permit(:status, :total)  # permits the KEY, not the VALUE — client picks any status string
```
**Rails-specific tell:** `permit(:status)` only stops unlisted *fields* from being mass-assigned; it does nothing to stop `status` being set to an illegal *value*. Look for the model callback or service object that should validate the transition — if `update(status: ...)` reaches `save` with no `before_save`/AASM guard in between, it's unenforced.

### Python / Django / Flask

Guarded:
```python
# transitions library
from transitions import Machine
machine = Machine(model=order, states=states, transitions=[
    {'trigger': 'pay', 'source': 'pending', 'dest': 'paid', 'conditions': 'payment_verified'},
])
order.pay()  # raises MachineError if source state doesn't match

# django-fsm
from django_fsm import FSMField, transition
class Order(models.Model):
    state = FSMField(default='pending')
    @transition(field=state, source='pending', target='paid', conditions=[payment_verified])
    def pay(self): ...
```
Unguarded:
```python
# View sets status straight from request body — no transition function involved
order.status = request.json['status']
order.save()

# Django ModelForm exposing the state field with all fields writable
class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = '__all__'   # or explicitly lists 'status' — client can set any value via POST
```
**Django-specific tell:** `fields = '__all__'` or an explicit `'status'`/`'is_verified'`/`'role'` in a `ModelForm`'s `fields` list, with no `clean_status()` validating the transition, is the mass-assignment path. Same risk in DRF: a `ModelSerializer` with `fields = '__all__'` and no `read_only_fields` covering the state column.

### Node / Express

Guarded (hand-rolled transition table — the common real-world shape when no library is used):
```js
const ALLOWED = { pending: ['paid'], paid: ['shipped', 'refunded'] };
function transition(order, next) {
  if (!ALLOWED[order.status]?.includes(next)) throw new Error('illegal transition');
  order.status = next;
}
```
Guarded (xstate):
```js
const orderMachine = createMachine({
  initial: 'pending',
  states: {
    pending: { on: { PAY: { target: 'paid', guard: 'paymentVerified' } } },
    paid: { on: { SHIP: 'shipped', REFUND: 'refunded' } },
  },
});
```
Unguarded:
```js
// Route handler sets whatever the client sent, no transition table
app.patch('/orders/:id', async (req, res) => {
  await Order.updateOne({ _id: req.params.id }, req.body);  // req.body may contain {status: 'refunded'}
});
```
**Tell:** `updateOne`/`findByIdAndUpdate` fed `req.body` directly (Mongoose) or a Sequelize `instance.update(req.body)` — the entire request body becomes the update document/attributes with no field allowlist and no transition check.

### Java / Spring

Guarded — Spring State Machine or an explicit transition-table service:
```java
@Configuration
public class OrderStateMachineConfig extends StateMachineConfigurerAdapter<OrderState, OrderEvent> {
    // transitions.withExternal().source(PENDING).target(PAID).event(PAY).guard(paymentGuard())
}
```
or a hand-rolled check:
```java
if (!order.getStatus().canTransitionTo(request.getStatus())) {
    throw new IllegalStateException("invalid transition");
}
```
Unguarded — generic binder onto the entity:
```java
@PatchMapping("/orders/{id}")
public Order update(@PathVariable Long id, @RequestBody Order patch) {
    Order order = repo.findById(id).orElseThrow();
    order.setStatus(patch.getStatus());   // any client-supplied enum value, no transition check
    return repo.save(order);
}

// Or worse: Spring's data binder applied to the whole entity
@ModelAttribute Order order;   // classic mass-assignment surface — any bindable field settable, including status/role/isAdmin
```
**Tell:** a `@RequestBody`/`@ModelAttribute` bound straight onto a JPA entity (not a dedicated DTO with only the intended-writable fields), followed by `repository.save(entity)` with no transition guard in between. If the entity has a `role`, `isAdmin`, `verified`, or `status` field and the DTO isn't a narrower shape than the entity, assume it's settable.

**What counts as a finding:** a writable status/role/state field reaching persistence via mass assignment (Rails strong params permitting the field, Django `ModelForm`/`ModelSerializer` with `__all__`, an unfiltered `req.body` update, or a `@RequestBody`/`@ModelAttribute` bound onto the raw entity) with no transition-table or guard check in between is **High** — it lets a client-controlled write reach a field the server never validates against legal transitions. If that field controls access or payment state (`role`, `is_admin`, `paid`, `verified`), escalate to **Critical**. A transition guard that exists but is missing one specific illegal edge (e.g., backward transition allowed) is **Medium**. A state machine library present and fully guarded, but lacking a guard clause purely for logging/observability, is **Low**.

---

## 2. Atomic vs. non-atomic balance/quota mutation

Maps to `/business-logic` Phase 1 (Value/Quantity Logic), Phase 5 (Idempotency), and Phase 6 (Quota Bypass).

**The question:** does a single statement own the read-modify-write, or is there a window between reading a numeric value and writing it back where a concurrent request can interleave?

### The universal tell

Two separate ORM/DB calls touching the same numeric column with no transaction, no lock, and no atomic expression between them is the racy shape — this holds regardless of language:
```
value = read(id)          # round-trip 1
value = value ± amount
write(id, value)          # round-trip 2 — anything that happened between 1 and 2 is lost or double-applied
```

### Ruby / Rails

Racy:
```ruby
user = User.find(id)
user.balance -= amount
user.save
```
Atomic:
```ruby
# Single UPDATE with a guard condition — fails if balance would go negative
User.where(id: id).where('balance >= ?', amount)
    .update_all('balance = balance - ' + amount.to_s)  # or use bind-safe arel/update_all with sanitized value

# Or optimistic locking via lock_version column (Rails' built-in optimistic locking)
user.update!(balance: user.balance - amount)  # raises ActiveRecord::StaleObjectError on concurrent write if lock_version mismatches

# Or pessimistic lock inside an explicit transaction
User.transaction do
  user = User.lock.find(id)   # SELECT ... FOR UPDATE
  user.update!(balance: user.balance - amount)
end
```

### Python / Django / Flask

Racy:
```python
user = User.objects.get(id=id)
user.balance -= amount
user.save()
```
Atomic:
```python
# Django F() expression — compiles to a single UPDATE, no read round-trip
User.objects.filter(id=id, balance__gte=amount).update(balance=F('balance') - amount)

# select_for_update inside an explicit transaction
with transaction.atomic():
    user = User.objects.select_for_update().get(id=id)
    user.balance -= amount
    user.save()

# Raw SQL with a guard clause
cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s AND balance >= %s", (amount, id, amount))
```
**Tell:** a `.get()` followed by attribute mutation and `.save()` on a balance/quota/counter field, with no `F()` expression and no `select_for_update()`/`transaction.atomic()` wrapping it, is racy — regardless of how far apart the read and write appear in the function.

### Node / Express (Sequelize / Mongoose / raw SQL)

Racy:
```js
const user = await User.findById(id);
user.balance -= amount;
await user.save();
```
Atomic:
```js
// Sequelize — atomic increment, single UPDATE
await User.increment({ balance: -amount }, { where: { id, balance: { [Op.gte]: amount } } });

// Mongoose — atomic findOneAndUpdate with a guard filter
await User.findOneAndUpdate({ _id: id, balance: { $gte: amount } }, { $inc: { balance: -amount } });

// Raw SQL guard clause
await db.query('UPDATE users SET balance = balance - $1 WHERE id = $2 AND balance >= $1', [amount, id]);

// Redis counter-style quota — atomic primitive
await redis.decrby(`quota:${userId}`, amount);   // or a Lua script for check-then-decrement in one round trip
```
**Tell:** `findById`/`findOne` followed by a plain object mutation and `.save()` on a numeric field is racy in both Sequelize and Mongoose. `findOneAndUpdate`/`updateOne` with `$inc` and a filter-level guard condition (not just an `if` in JS after the read) is atomic.

### Java / Spring / JPA / Hibernate

Racy:
```java
User user = userRepository.findById(id).orElseThrow();
user.setBalance(user.getBalance() - amount);
userRepository.save(user);   // no version check — last writer wins, lost update
```
Atomic:
```java
// Optimistic locking via @Version
@Entity
class User {
    @Version
    private Long version;
    private BigDecimal balance;
}
// save() now throws OptimisticLockException on concurrent modification — caller must retry

// Or a derived query with a guard, executed as a single UPDATE
@Modifying
@Query("UPDATE User u SET u.balance = u.balance - :amount WHERE u.id = :id AND u.balance >= :amount")
int debit(@Param("id") Long id, @Param("amount") BigDecimal amount);
// caller checks the returned row count == 1 to confirm the debit applied

// Or pessimistic lock
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT u FROM User u WHERE u.id = :id")
User findByIdForUpdate(@Param("id") Long id);
```
**Tell:** an entity with a numeric balance/quota field but no `@Version` column, combined with a service method that does `getX()` → arithmetic → `setX()` → `save()`, is the racy shape. Grep for `@Version` on entities that also expose a balance/counter field — its absence on a money-bearing entity is itself worth flagging even without confirming a concrete race.

### Quota-specific variant: check-then-act across two calls

Beyond balance mutation, the same non-atomic shape shows up as a separate "check quota" call followed by a separate "consume quota" call (e.g. `if (getUsage(user) < limit) { incrementUsage(user) }`) — the check and the increment are two round-trips, so concurrent requests can all pass the check before any of them commits the increment. Look for this pattern anywhere a quota, seat count, or rate-limit counter is read and written in separate statements rather than one atomic increment-with-guard.

**What counts as a finding:** two separate calls (read then write) mutating a balance, credit, or quota column with no transaction/lock/atomic expression between them is **Critical** if the field represents money or a security-relevant limit (account balance, credits, seats-with-billing-impact) and **High** for other counters (usage stats, non-monetary quotas) — because it's a straightforward double-spend/TOCTOU race, not a theoretical one. An entity that has optimistic locking (`@Version`, `lock_version`) present but a service path that ignores the resulting exception (swallows `OptimisticLockException`/`StaleObjectError` and retries with stale data) is **Medium**. Atomic primitives used correctly but without a guard clause (e.g., `F()` decrement with no `balance__gte` filter, allowing the balance to go negative) is **High** — the race is closed but the value-logic bound isn't enforced.

---

## 3. Fail-open exception-handling shapes

Maps to `/business-logic` Phase 4 (Trust Boundary/BFLA) and Phase 6 (Quota Bypass) — the source-level root cause of many bypasses live-testing finds as "the check just isn't there under load/error conditions."

**The question:** when the authorization, entitlement, rate-limit, or feature-flag check itself throws or times out, does the code path deny by default, or does the exception handler quietly let the request through?

### Python

Fail-open:
```python
try:
    if not user.has_permission(resource):
        raise PermissionError
except Exception:
    pass  # swallowed — falls through to the operation below, effectively granting access

# Or an explicit fallback
try:
    allowed = entitlement_service.check(user, feature)
except (TimeoutError, ConnectionError):
    allowed = True   # fail open on service unavailability
```
Fail-closed counterexample:
```python
try:
    allowed = entitlement_service.check(user, feature)
except (TimeoutError, ConnectionError):
    allowed = False   # or re-raise, or return 503 — never silently grant
if not allowed:
    abort(403)
```

### Java / Spring

Fail-open:
```java
boolean allowed;
try {
    allowed = authzService.check(user, resource);
} catch (Exception e) {
    allowed = true;   // or: return true; inside a permission-check method's catch block
}

// Empty catch around a permission check
try {
    accessControl.enforce(user, resource);
} catch (AccessDeniedException e) {
    // swallowed — no re-throw, execution continues to the protected operation
}
```
Fail-closed counterexample:
```java
try {
    accessControl.enforce(user, resource);
} catch (AccessDeniedException e) {
    throw e;   // propagate — let the framework return 403
} catch (Exception e) {
    throw new AccessDeniedException("authz check failed", e);  // treat any authz-path error as deny
}
```

### Node / Express

Fail-open middleware:
```js
async function requireAuth(req, res, next) {
  try {
    req.user = await verifyToken(req.headers.authorization);
    next();
  } catch (err) {
    next();   // BUG: calls next() instead of next(err) — request proceeds unauthenticated
  }
}
```
Fail-closed counterexample:
```js
async function requireAuth(req, res, next) {
  try {
    req.user = await verifyToken(req.headers.authorization);
    next();
  } catch (err) {
    res.status(401).json({ error: 'unauthorized' });   // or next(err) with an error handler that denies
  }
}
```

### Feature flags, rate limiters, circuit breakers (any language)

Fail-open tells to grep for:
```
featureFlags.getBoolean(flagName, true)          # default-true fallback on flag-service error
launchDarkly / Unleash / ConfigCat client call with a `true`/permissive default value
ratelimiter.check(key).catch(() => allow = true)  # or: catch (RedisConnectionException) { allow = true; }
circuitBreaker.fallback(() -> grantAccess())      # fallback function grants instead of denies
```
Fail-closed counterexample: the same calls with a `false`/restrictive default, or a fallback that returns a 429/403/503 instead of proceeding.

**What counts as a finding:** a swallowed exception or a true/allow default sitting on the path of an authorization, entitlement, or verification check is **High** — the server-side guard is only as strong as its unhappy path, and an attacker who can trigger the error condition (timeout, malformed token, downstream outage) gets an implicit bypass. If the guarded operation involves money, admin access, or identity verification, escalate to **Critical**. The same fail-open shape on a pure rate-limiter or non-security feature flag (no access/money impact) is **Medium**. A caught exception that's logged and correctly re-thrown/denied, but with an overly broad `except Exception`/`catch (Exception e)` catching more than intended (masking bugs without changing the allow/deny outcome), is **Low**.

---

## 4. Time/date trust patterns

Maps to `/business-logic` Phase 7 (Time & Date Manipulation).

**The question:** is the value used to decide "is this still valid?" something the server computed and owns, or does the check re-read a timestamp the client supplied on this request?

### Client-supplied date reaching the check directly

```python
# Flask/Django — request body value compared straight to "now"
if request.json['valid_until'] > datetime.utcnow().isoformat():
    grant_access()
```
```java
// Spring — bound request param used directly in validation logic
@PostMapping("/licenses/validate")
public boolean validate(@RequestParam Date validUntil) {
    return validUntil.after(new Date());   // validUntil came from the client on THIS request
}
```
```js
// Express — client sends the expiry it wants checked against
if (new Date(req.body.expiresAt) > new Date()) { /* treat as valid */ }
```
```ruby
# Rails — same shape
if Time.parse(params[:valid_until]) > Time.current
  grant_access
end
```

### Server-computed expiry (correct pattern)

```python
# Value set once at creation, server-side, never re-read from client input on the check path
license.valid_until = created_at + timedelta(days=365)   # computed at issuance
license.save()
# ...later, on the check path:
if license.valid_until > timezone.now():   # reads the STORED value, not anything from the current request
    grant_access()
```
```sql
-- Expiry enforced at the database level, comparing a stored column to server time
SELECT * FROM licenses WHERE id = :id AND valid_until > NOW();
```
The distinguishing question when reading a validity/expiry check: trace backward from the comparison — does the right-hand or left-hand operand originate from `request.*`/`req.body`/`@RequestParam`/`params[...]` on the *current* request, or from a column/attribute that was only ever written during creation/renewal (a different, privileged code path)? If the same field name appears both as a request parameter the client can set and as the value later checked, treat it as a live finding.

**What counts as a finding:** a client-supplied date/timestamp field reaching an expiry, validity, or access-window check unfiltered is **High** — this is a direct trust-boundary violation on time, letting an attacker extend a license, subscription, promo window, or token validity indefinitely by resending a favorable date. If the extended validity gates payment or admin access, escalate to **Critical**. A client-supplied date that reaches the check but is clamped/validated server-side against a maximum (e.g., "extend by at most 30 days from now, ignoring anything further") is **Low** — the trust boundary is still crossed but bounded. Server time itself sourced from an untrusted or client-adjustable source (rare, but e.g. trusting a client-sent `X-Client-Time` header for any decision) is **Medium**.

---

## 5. Predictable ID/code generation

Maps to `/business-logic` Phase 8 (Reference & Authorization Code Predictability).

**The question:** does the generator for anything used as a proof-of-access or a reference to a specific resource draw from a CSPRNG with enough output space, or from something an attacker can predict or enumerate?

### Weak generators to grep for

```python
# Plain DB auto-increment exposed as the public reference/order number
order.id  # serial/auto-increment PK used directly as the customer-facing order number

# Timestamp-based "unique" code
code = str(int(time.time()))                     # fully predictable, collides under load
reference = f"{int(time.time())}-{user_id}"      # timestamp concatenation

# Weak PRNG for a short code
code = str(random.randint(100000, 999999))       # random, not secrets — not cryptographically secure, and 6 digits is only ~20 bits
```
```java
// Sequential ID or a non-CSPRNG generator
long referenceNumber = idSequence.nextValue();               // sequential, enumerable
String code = String.valueOf(new Random().nextInt(999999));  // java.util.Random is not a CSPRNG — seed-predictable
```
```js
// Snowflake-style ID exposed publicly without wrapping
const orderId = snowflake.generate();   // encodes timestamp + machine ID + sequence — enumerable/predictable if exposed raw as the public reference
```
```ruby
# Rails default id used as a public-facing reference (order confirmation URL, invite link)
"/orders/#{order.id}/confirm"   # sequential integer PK directly in a URL used as a capability
```

### Strong generators

```python
import secrets
token = secrets.token_urlsafe(32)   # CSPRNG, 256 bits of entropy before base64
```
```java
import java.security.SecureRandom;
byte[] bytes = new byte[32];
new SecureRandom().nextBytes(bytes);   // CSPRNG
```
```js
const crypto = require('crypto');
const token = crypto.randomBytes(32).toString('hex');   // CSPRNG
```
```ruby
SecureRandom.uuid            # UUIDv4 — fine for a reference number, not derived from PK
SecureRandom.urlsafe_base64(32)
```
UUID version matters: a real **UUIDv4** (random) is an acceptable opaque reference. **UUIDv1** encodes a timestamp and the generating node's MAC address in the value itself — if it's exposed publicly as a resource reference, that's an information-disclosure and predictability finding in its own right (an attacker can extract creation time and, in some environments, infer the originating host), independent of any other weakness. Grep for `uuid1()`/`Guid.NewGuid()` on .NET pre-`Guid.CreateVersion7`/any UUID library call explicitly requesting version 1, and check what the field is used for.

A signed/HMAC'd reference token (`hmac.new(secret, f"{order_id}".encode(), sha256).hexdigest()` appended to or replacing the raw ID) is also acceptable — it doesn't need to be random if it can't be forged without the server secret, but check that the secret isn't derived from a guessable per-user value and that the comparison uses a constant-time compare (`hmac.compare_digest`, not `==`).

**What counts as a finding:** a public-facing reference/confirmation/order/invite code drawing from a DB auto-increment, `random.randint`/`java.util.Random`/`Math.random()`, or timestamp concatenation, where possessing that code alone grants access to the resource (view an order, redeem a voucher, confirm a transaction), is **High** — full or partial enumerability of a proof-of-access value. If the resource gated is payment, an account-recovery flow, or admin invite, escalate to **Critical**. A UUIDv1 (or any version leaking creation timestamp/host) used as a public reference where the timestamp leak alone has no further exploitation path is **Low**; where it materially narrows a brute-force window (e.g., combined with a short code also generated at that time) it's **Medium**. A CSPRNG-generated value with adequate length but no rate limiting on the endpoint that checks/redeems it is a **Medium** (the generation is sound, but brute-forcing isn't rate-limited — cross-reference `/business-logic` Phase 6).

---

## Cross-reference summary

| This file's section | `/codebase` Phase 5d narrative topic | `/business-logic` live-testing phase |
|---|---|---|
| 1 | State machine integrity / Workflow-step-order enforcement | Phase 2 (Workflow Bypass), Phase 3 (State Machine Abuse) |
| 2 | Idempotency & atomicity / Value-quantity logic | Phase 1 (Value/Quantity Logic), Phase 5 (Idempotency & Replay), Phase 6 (Quota Bypass) |
| 3 | Fail-safe defaults / Quota-rate-limit enforcement location | Phase 4 (BFLA), Phase 6 (Quota Bypass) |
| 4 | Time/date trust | Phase 7 (Time & Date Manipulation) |
| 5 | Predictability of generated values | Phase 8 (Reference & Authorization Code Predictability) |
