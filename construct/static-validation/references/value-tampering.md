# value-tampering: Value, quantity, price and limit tampering

Covers negative or zero quantities, client-supplied prices/totals/discounts, rounding and
overflow abuse, and limits or quotas that are not enforced server-side. (Use this class for all
of them; `negative-quantity`, `price-tampering`, `quota-bypass` are aliases, not classes.)

## Claim to verify
A numeric value the attacker controls (or a value the server should compute but takes from the
client) reaches money, stock, credit, quota or limit logic without bounds, so the attacker gains
value or exceeds a limit.

## Refute if
- The value is validated server-side with the right bounds before use (`gt=0` / `ge=1` in
  Pydantic, `@Min(1)`/`@Positive` with `@Valid`, Joi/zod `.positive().int()`, explicit
  `if qty < 1: reject`), on every path that writes it (create **and** update, single and bulk).
- The server ignores the client value and recomputes it (price from the catalogue, total from
  line items, discount from a server-side promotion record).
- A DB constraint rejects it (`CHECK (quantity > 0)`, unsigned column) and the error aborts the
  operation.
- The arithmetic uses decimal types with explicit rounding rules that cannot favour the client
  (`Decimal` + `quantize`, `BigDecimal` with `RoundingMode`).
- The limit is checked against server-side counts atomically (see `race-condition` if the check
  is separate from the write).

## Framework protections to check
- Type-only validation (`int`, `number`) does not bound sign or size.
- Client-side `min="1"` attributes and UI disabling are not validation.
- Floats for money (`0.1 + 0.2`), per-item rounding, currency taken from the client.
- Fixed-width integer overflow (Java `int`, Go `int32`, C# `int` unchecked) when multiplying
  price x quantity.
- Discount/coupon application endpoints callable repeatedly or after totals are fixed.
- Limits enforced on one endpoint and not on another (import, update, API vs UI).

## confirmed_static when
The cited value enters from the request, reaches a cited computation or persistence that
affects money, stock, credits or limits, and no bound, recomputation or constraint exists on the
path.

## Common false positives
- Negative values that are legitimate (refund line items created by trusted code, adjustments by
  admins).
- Values bounded by an enum or a server-side lookup.

## Severity
Direct financial gain (negative total, free goods, arbitrary discount): `high`/`critical`.
Quota/limit bypass with billing impact: `high`; without: `medium`.

## Remediation
Validate bounds server-side on every write path, recompute monetary values from trusted data,
and add DB constraints.
