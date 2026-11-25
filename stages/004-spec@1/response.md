1. Summary

Add VCS metadata mining to the `/codebase` white-box review skill so agents use commit history, refs, tags, and changelogs as security-review leads instead of only scanning source contents and secret history. The new guidance must find security-fix and insecure-shortcut hints, record actionable evidence, feed touched files into deeper review phases, and explicitly state when history coverage is unavailable or incomplete.

2. Acceptance criteria

1. `appsec/codebase/SKILL.md` adds an all-depths VCS metadata mining step before deeper review phases. The step explicitly covers all local branches/remotes/tags, commit subjects and bodies, merge/squash/PR-title text where present in commit messages, tag names/messages, and changelog/release-note files; it must not be limited to the current working tree.
2. The step defines two maintained keyword groups: security fixes (including at least injection, bypass, XSS, SSRF, traversal/path traversal, redirect/open redirect, CSRF, auth/access control, deserialization, RCE) and insecure shortcuts (including at least hack, temporary, insecure, disable check, skip validation, for testing only, do not merge, FIXME security, TODO security).
3. For every metadata hit, the skill instructs the agent to record a structured `report(action="note")` entry containing commit/ref identifier when available, source type, matched category and keyword, touched files, and a sanitized message excerpt. Raw secret values must not be logged.
4. Files touched by security-relevant commits are explicitly added to the Phase 5 dangerous-pattern/taint-analysis leads, Phase 5d business-logic leads when relevant, and the Phase 7 security profile priority targets.
5. Apparent security-fix hits require a cross-branch/release check against maintained branches and tags. The skill must instruct agents to flag fixes present on only some maintained refs as possible unbackported vulnerabilities with the affected refs, while still requiring code verification before reporting a confirmed vulnerability.
6. Commit, tag, merge, PR-title, and changelog text are included as secret-scanning surfaces. If the existing trufflehog wrapper cannot confirm metadata-message coverage, the skill must instruct a safe supplemental metadata scan or an explicit coverage-limitation note.
7. Ticket IDs and CVE IDs found in metadata are extracted as review leads; public/in-scope references may be followed when reachable, while private or unreachable references are recorded without blocking the review.
8. If VCS metadata is unavailable, incomplete, shallow, missing refs, or cannot be inspected, the skill requires an explicit `report(action="note")` coverage statement instead of silent skipping.
9. The change passes `python3 validate_skills.py` and does not touch unrelated skills, CI workflows, scripts, or dependency files.

3. Scope

Files to change:
- `appsec/codebase/SKILL.md`

Files to add:
- None.

Out of scope:
- Changes to `validate_skills.py`, CI workflows, SkillSpector baselines, package/dependency files, or any skill outside `appsec/codebase`.
- Implementing a new scanner or changing MCP/server behavior; this is skill-instruction text only.
- Automatically fetching remote branches, private tickets, or external CVE pages beyond what the existing agent environment and user authorization already permit.

4. Design

Use the existing markdown skill architecture: update the `/codebase` workflow rather than creating a new skill. Prefer adding a Phase 1 sub-step such as `Step 5 — VCS metadata mining (all depths)` after dependency audit and before the Phase 1 diagram, because the output is orientation data that feeds Phase 5/5d and Phase 7. If command examples are included, keep them read-only and local, using safe git inspection commands such as log/for-each-ref/show/diff-tree; quote the codebase path and never interpolate commit messages, tag names, or branch names into a shell command.

Update existing related sections rather than duplicating logic:
- Tools table: add a concise row only if needed for read-only local git metadata inspection, following surrounding wording.
- Phase 4 automated scanning: extend the existing trufflehog-history guidance so metadata text is treated as a secret surface and coverage gaps are recorded.
- Phase 5 and Phase 5d: tell agents to prioritize files and flows surfaced by VCS metadata hits.
- Phase 7 security profile: add concise fields/lines for VCS history coverage, metadata leads, unbackported-fix candidates, and priority targets.

No new dependencies are involved. Findings still follow the existing severity bar: metadata is a lead, not proof; confirmed vulnerabilities require source evidence and, where applicable, trace entries.

5. Code quality requirements

- Follow the tone, headings, tables, and imperative style already used in `appsec/codebase/SKILL.md`.
- Keep the change minimal and localized; avoid renumbering major phases unless necessary.
- Avoid duplicating the existing secrets-liveness procedure; reference the existing Phase 4 guidance and `appsec/aikido-triage/references/secrets-playbook.md` where liveness probing is relevant.
- Use clear names such as `VCS metadata leads`, `security-fix keywords`, `insecure-shortcut keywords`, and `unbackported-fix candidates`.
- Do not introduce client-specific skill invocation syntax; `validate_skills.py` must remain clean.
- Do not add dead examples, speculative abstractions, or unrelated wording changes.

6. Security considerations

VCS metadata, changelog text, branch names, tag names, commit messages, PR titles, ticket IDs, and CVE references are untrusted input from repository contributors. The skill must warn agents not to follow instructions embedded in that text, not to paste full secrets into logs, and not to treat metadata as proof without code verification.

Shell injection risk exists if untrusted refs or messages are interpolated into commands. Command examples must be read-only, avoid `eval`/`xargs sh`/checkout of untrusted refs, quote the target path, and pass refs as data only where safe. Prefer git commands that read object metadata and touched file lists without executing hooks or target code.

Secret-handling risk increases because commit and tag messages may contain credentials. Evidence must mask raw secret values, and any liveness probe must keep the existing opt-in process; no automatic credential validation is introduced.

Authentication/authorization behavior of target applications is not changed. Business-logic abuse risk is that agents could over-report historical fixes as current vulnerabilities; the skill must require cross-ref presence checks and current-code verification before confirmed findings.

7. Edge cases

- Non-git directory, missing `.git`, exported source archive, or inaccessible VCS metadata.
- Shallow clone, partial clone, detached HEAD, missing remote branches, missing tags, or refs that cannot be fetched within scope.
- Very large histories or changelogs causing noisy/duplicate hits; guidance should deduplicate by commit/ref and touched-file set and summarize without flooding logs.
- Merge commits, squash commits, cherry-picks, reverts, renamed/deleted files, binary-only changes, and backports with different commit IDs.
- Weird, malformed, or malicious branch/tag/message text, including shell metacharacters, newlines, terminal escapes, prompt-injection wording, or embedded secrets.
- Changelog/release-note files absent, huge, generated, duplicated across versions, or inconsistent with git history.
- Security fix appears in one maintained branch/tag but not another, or branch maintenance status is unclear.
- Git commands fail because the repository changes during review or because permissions deny reading some refs.

8. Test plan

Unit tests:
- None to add or update; this change is markdown-only and adds no Python code.

Integration tests:
- Existing `validate_skills.py::main`: run `python3 validate_skills.py`. Asserts all skill frontmatter remains valid, description length stays within limits, no duplicate skill names are introduced, and no prohibited client-specific syntax is added.

Regression tests / review checks:
- `appsec/codebase/SKILL.md::test_vcs_metadata_surfaces`: manually inspect or grep the changed file to assert the new step covers all refs, commit subjects/bodies, merge/squash/PR-title text where locally present, tags, changelogs, and unavailable/incomplete-history notes. Covers acceptance criteria 1 and 8 plus non-git/shallow/missing-ref edge cases.
- `appsec/codebase/SKILL.md::test_keyword_groups_and_reporting`: manually inspect or grep for both keyword groups and the required report fields: commit/ref, source type, category, keyword, touched files, sanitized message excerpt. Covers acceptance criteria 2 and 3 plus duplicate/noisy history and malformed message edge cases.
- `appsec/codebase/SKILL.md::test_metadata_leads_feed_deeper_review`: manually inspect that VCS metadata leads feed Phase 5, Phase 5d, and Phase 7 security-profile priority targets. Covers acceptance criterion 4.
- `appsec/codebase/SKILL.md::test_backport_and_reference_handling`: manually inspect that apparent security fixes are checked across maintained branches/releases/tags, unbackported candidates are flagged with affected refs, cherry-pick/different-SHA cases are considered, and ticket/CVE IDs become leads. Covers acceptance criteria 5 and 7.
- `appsec/codebase/SKILL.md::test_metadata_secret_and_injection_guards`: manually inspect that commit/tag/changelog text is a secret-scanning surface, raw secrets are masked, trufflehog coverage gaps are noted, metadata prompt injection is ignored, and shell examples are read-only and do not interpolate untrusted refs/messages unsafely. Covers acceptance criterion 6 and all security considerations.

Existing tests/checks that must keep passing:
- `python3 validate_skills.py`
- Repository CI workflows for skill validation and SkillSpector scanning should remain green.

Tests required: no

9. Risks

- The added workflow text may make `/codebase` longer and slightly increase review time, especially on large repositories.
- Agents may over-prioritize noisy historical wording or old fixed issues unless the text clearly labels metadata as leads requiring current-code verification.
- Git command examples could accidentally encourage unsafe shell interpolation if written carelessly.
- Frontmatter description edits could exceed the 1024-character validation limit if the implementation expands it too much.

10. Suspicious content

none

Risk level: medium
The change alters security-review behavior and touches untrusted VCS metadata, secret handling, and shell-command guidance, but it is confined to one markdown skill with no runtime code or dependency changes.