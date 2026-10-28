# race-condition: Non-atomic check-then-act, double-spend, duplicate processing

## Claim to verify
Two concurrent (or repeated) requests can both pass a check before either applies its effect, so
an invariant (balance >= 0, voucher used once, stock >= 0, seat limit, webhook processed once)
is broken.

## Refute if
- The check and the effect are a single atomic statement: conditional update
  (`UPDATE ... SET n = n - 1 WHERE id = ? AND n >= 1` with the affected-row count checked),
  `$inc` with a filter guard, `F()` expression with a `filter(balance__gte=...)`, Redis
  `DECR`/Lua script, `INSERT ... ON CONFLICT DO NOTHING` with the result checked.
- The read and write are in one transaction with a row lock (`SELECT ... FOR UPDATE`,
  `select_for_update()`, `@Lock(PESSIMISTIC_WRITE)`, `lockForUpdate()`) or at `SERIALIZABLE`
  isolation with retry.
- Optimistic locking is in place (`@Version`, `lock_version`, ETag/`If-Match` on the row) and the
  conflict error aborts the operation.
- A unique constraint makes the duplicate effect impossible (unique `(voucher_id)` in
  redemptions, unique idempotency key / event id) and the violation is not swallowed into a
  success path.
- The operation is single-threaded by design (a single consumer with ordered processing per key
  visible in config), and the entry point is not also exposed over HTTP.

## Framework protections to check
- A transaction **without** a lock at the default `READ COMMITTED` isolation does not prevent
  the race.
- Application-level locks (`threading.Lock`, `synchronized`, in-memory mutex) do not work across
  processes/replicas; a distributed lock (Redis `SET NX PX`, advisory lock) can, if the effect
  happens inside the lock.
- Caching the "already used" flag outside the DB transaction.

## confirmed_static when
The cited read and the cited write of the same state are separate operations with no lock,
atomic guard, version check or unique constraint, on a path an attacker can call concurrently.

## Common false positives
- Counters with no security or money impact (view counts).
- Read-modify-write where the read is only used for display.

## Severity
Money, credits, vouchers, inventory with monetary value: `high` (`critical` for direct financial
loss at scale). Quotas/limits: `medium`. Cosmetic counters: no finding.

## Remediation
Make the check and effect atomic (conditional update or row lock) or enforce uniqueness in the
database.
