# Domain glossary

Business terms that appear in PR descriptions and code, what they mean, and the invariants that
security review should hold them to. Business-logic hypotheses should reuse these names in
`business_flows_touched`, `title` and `description`.

| Term | Meaning | Invariants | Where enforced |
|---|---|---|---|
| TODO(appsec): e.g. `workspace` | Tenant boundary; all customer data belongs to exactly one workspace | Users only see workspaces they are members of | TODO(appsec) |
| TODO(appsec): e.g. `seat` | Paid user slot in a workspace | Active members <= purchased seats | TODO(appsec) |
| TODO(appsec): e.g. `payout` | Transfer of funds to a merchant | Only `finance` role; amount <= available balance; once per payout id | TODO(appsec) |
| TODO(appsec): e.g. `order` lifecycle | `draft -> placed -> paid -> shipped -> delivered`, side exits `cancelled`, `refunded` | `refunded` only from `paid`/`shipped`/`delivered`; refund amount <= captured amount | TODO(appsec) |

## Flows

TODO(appsec): list the main business flows (sign-up, invite member, checkout, refund, payout,
data export, account deletion) with the endpoint or service that implements each step.
