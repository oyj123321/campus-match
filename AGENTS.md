# Repository Workflow

- Every push that changes project code must include a corresponding update to
  `CHANGELOG.md`. This is an explicit owner requirement.
- Describe the actual behavior changes, fixes, and relevant deployment notes.
  Keep unfinished work under `Unreleased`; do not claim that a push deploys it.
- Before pushing, fetch the target branch, preserve existing local edits, and
  integrate remote changes without force-pushing over other contributors.
