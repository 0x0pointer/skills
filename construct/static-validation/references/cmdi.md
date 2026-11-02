# cmdi: OS command injection

## Claim to verify
Attacker data reaches a command executed by a shell (metacharacter injection), or reaches the
argument list of a program in a way that injects options or a different program.

## Refute if
- The call uses an argv array with no shell (`subprocess.run([...])` without `shell=True`,
  `execFile`, `spawn` without `shell: true`, `ProcessBuilder(List)`, Go `exec.Command(bin, args...)`,
  .NET `ArgumentList`) **and** the program is fixed **and** option injection is impossible
  (value is preceded by `--`, validated against `^[^-]`, or the program ignores option-like args).
- The value is strictly validated (allowlist, numeric coercion, strict regex such as
  `^[a-z0-9]{1,32}$`) before use.
- Each argument is quoted for the shell (`shlex.quote`, `escapeshellarg`) when a shell is used,
  and no part of the command template itself is user-controlled.

## Framework protections to check
- `shell=True`, `os.system`, `os.popen`, `exec`, `execSync`, `sh -c`, `cmd /c`, backticks,
  `Runtime.exec(String)` (tokenises on spaces, no shell, but still a problem if the program is
  user-controlled).
- Option injection in argv calls: `git` (`--upload-pack=`), `tar` (`--checkpoint-action=`),
  `curl` (`-o`), `ssh` (`-oProxyCommand=`), `find` (`-exec`), `rsync` (`-e`).
- Indirect: environment variables, `PATH` manipulation, filenames starting with `-`.

## confirmed_static when
A cited source reaches a cited shell invocation (or option position of a sensitive program) on
a reachable path with no effective validation or quoting.

## Common false positives
- Command strings built entirely from constants or server config.
- `shlex.quote` applied to every interpolated value.

## Severity
Reachable command injection is remote code execution: `critical` (anonymous/any user) or
`high` (admin only).

## Remediation
Use an argv array without a shell, validate against an allowlist, and pass `--` before
user-supplied positional arguments.
