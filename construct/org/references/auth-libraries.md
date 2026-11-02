# Internal authentication and authorization libraries

One section per library. Keep each entry factual: what it guarantees, how to recognise its use,
and how it is commonly misused.

## TODO(appsec): <library name, e.g. acme-auth>

- **Languages / frameworks:** TODO(appsec)
- **What it does:** TODO(appsec) (e.g. validates the session JWT issued by the IdP, pins `RS256`,
  checks `iss`, `aud`, `exp`, and exposes the principal as `request.principal`).
- **How to recognise use:** TODO(appsec) (e.g. `@acme_auth.require_login`,
  `app.use(acmeAuth())`, `[AcmeAuthorize]`).
- **Roles and permissions:** TODO(appsec) (e.g. `@acme_auth.require_permission("orders:refund")`;
  permission names are `<resource>:<action>`).
- **Ownership / tenancy helpers:** TODO(appsec) (e.g. `acme_auth.scope(query)` adds
  `tenant_id = principal.tenant_id`).
- **Fails closed?** TODO(appsec) (what happens on IdP outage, malformed token, missing header).
- **Known misuse:** TODO(appsec) (e.g. `optional_login` used on routes that need login;
  `principal.claims` read before verification in websocket handlers).

## TODO(appsec): <service-to-service auth, e.g. internal mTLS / signed service tokens>

- **What it guarantees:** TODO(appsec)
- **Which services are callable from the internet:** TODO(appsec)
- **Headers that are trusted only behind the gateway:** TODO(appsec) (e.g. `X-User-Id` set by the
  gateway; a service reachable without the gateway must not trust it).
