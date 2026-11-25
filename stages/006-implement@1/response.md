Implemented the approved spec in `appsec/codebase/SKILL.md` only.

What I changed:
- Added a new Phase 1 **Step 5 — VCS metadata mining (all depths)** covering all local branches/remotes/tags, commit subjects/bodies, merge/squash/PR-title text when present, tag names/messages, and changelog/release-note files.
- Added the two maintained keyword groups:
  - **security-fix keywords**
  - **insecure-shortcut keywords**
- Added required structured `report(action="note")` guidance for metadata hits, including commit/ref, source type, category, keyword, touched files, and sanitized excerpt.
- Added guidance to:
  - extract ticket/CVE IDs as leads,
  - check apparent security fixes across maintained branches/tags for **unbackported-fix candidates**,
  - explicitly note incomplete/unavailable VCS coverage,
  - treat metadata text as a secret-scanning surface,
  - avoid following instructions embedded in metadata,
  - use only safe, read-only git inspection examples.
- Wired metadata leads into:
  - **Phase 5** dangerous-pattern review,
  - **Phase 5d** business-logic review,
  - **Phase 7** security profile / priority targets.
- Extended Phase 4 trufflehog guidance to require metadata-message coverage confirmation or an explicit limitation note.

Validation run:
- Manual review checks via `grep` matching the spec’s named review checks
- `python3 validate_skills.py` ✅

Test coverage by acceptance criterion:
- **AC 1 & 8**: `test_vcs_metadata_surfaces` (manual grep check)
- **AC 2 & 3**: `test_keyword_groups_and_reporting` (manual grep check)
- **AC 4**: `test_metadata_leads_feed_deeper_review` (manual grep check)
- **AC 5 & 7**: `test_backport_and_reference_handling` (manual grep check)
- **AC 6**: `test_metadata_secret_and_injection_guards` (manual grep check)
- **AC 9**: `python3 validate_skills.py`