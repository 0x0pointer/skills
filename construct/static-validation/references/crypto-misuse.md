# crypto-misuse: Cryptographic misuse

## Claim to verify
A security property (confidentiality, integrity, unpredictability, password protection) relies
on a cryptographic primitive that is used incorrectly: weak or non-cryptographic randomness for
secrets, weak password hashing, unauthenticated or ECB encryption, static/reused IVs or nonces,
hard-coded keys, non-constant-time comparison of secrets, disabled TLS verification, or
signatures that are not verified.

## Refute if
- The value protected is not security-relevant (cache keys, request ids for logs, A/B bucket
  assignment, non-secret identifiers).
- The weak primitive is used for a non-security purpose (MD5 for ETags or dedupe, SHA-1 for git
  object ids).
- The randomness source is a CSPRNG (`secrets`, `crypto.randomBytes`, `crypto.randomUUID`,
  `SecureRandom`, `crypto/rand`, `RandomNumberGenerator`, `random_bytes`).
- Disabled TLS verification is confined to test code or a local-only dev profile that cannot be
  enabled in production (verify the config path).

## Framework protections to check
- Tokens/codes from `random`, `Math.random`, `java.util.Random`, `math/rand`, `rand`/`mt_rand`,
  `uniqid`, timestamps, or sequential ids used as proof of access (reset, invite, voucher).
- Passwords hashed with fast hashes (`md5`, `sha1`, `sha256` without a KDF) instead of bcrypt,
  scrypt, Argon2 or PBKDF2 with high iteration counts.
- AES in ECB, CBC without MAC, GCM with a reused nonce, hard-coded keys/IVs in source.
- JWT: `alg: none` accepted, `verify=False`, missing `algorithms` allowlist (RS/HS confusion),
  `decode` used instead of `verify`.
- `==` on HMACs/tokens instead of `hmac.compare_digest`, `crypto.timingSafeEqual`,
  `MessageDigest.isEqual`, `hash_equals`.
- `verify=False`, `InsecureSkipVerify`, `rejectUnauthorized: false`, trust-all `TrustManager`.

## confirmed_static when
The cited misuse protects a cited security-relevant value on a reachable production path, and
an attacker can feasibly exploit it (predict, brute-force, forge, decrypt, MITM).

## Common false positives
- `uuid4()` for reference ids (cryptographically random on all mainstream runtimes).
- Legacy hash verified only to migrate users to a strong hash on next login.

## Severity
Forgeable auth tokens or predictable reset tokens: `critical`/`high`. Weak password hashing:
`high`. Timing compare on HMAC: `medium`. Hardening issues without a concrete attack: `low`.

## Remediation
Use the platform CSPRNG, a password KDF, authenticated encryption with random nonces, a
verified signature with a pinned algorithm, and constant-time comparison.
