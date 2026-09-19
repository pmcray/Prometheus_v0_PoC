# Branch Topology and History Unification

**Status:** `main` is the trunk. Branch from it, and open pull requests against it.

## Why this document exists

Until this change the repository contained **two unrelated git histories**. They had
different root commits, so `git merge-base` returned nothing between them and no
ordinary merge was possible. Anyone branching from the nominal default (`master`)
was working on a stale lineage that did not contain the current project.

| Lineage | Root commit | Branches | Tip date |
|---------|-------------|----------|----------|
| A (legacy) | `f352e0c` | `master` (14 commits) → `v0.69` (202 commits) | 2026-02-17 |
| B (current) | `12dd474` | `wp16-notebook-only` (50) → `claude/arc-agi-3-notebook-XVCzt` (92) | 2026-06-11 |

Lineage B is a strict **superset** of lineage A in content: it carries 211 modules
under `prometheus/` against lineage A's 115, and **no file exists in `v0.69` that is
absent from lineage B**. Lineage A was re-imported rather than merged at some point,
which is what created the second root.

`main` is therefore cut from lineage B. Nothing is lost by retiring lineage A.

## What `main` fixes

Naming the trunk `main` repairs two things that had been silently broken:

- **CI now runs.** `.github/workflows/test-notebooks.yml` triggers on `push` and
  `pull_request` against `main`. That branch did not previously exist anywhere among
  the repository's branches, so the workflow had never fired — 104 test files and 68
  notebooks were ungated.
- **The Colab badges resolve.** The README carries 14 badges pointing at
  `.../blob/main/notebooks/...`, and six other files carry one each. All 20 were 404ing
  because the default branch was `master`. All nine distinct notebooks they reference
  are present on `main`.

## Branch inventory

- **`main`** — the trunk. All new work branches from here.
- **`claude/arc-agi-3-notebook-XVCzt`** — active ARC-AGI-3 development (bridge v23→v35).
  Shares `main`'s history; still live.
- **`master`, `v0.69`** — legacy lineage A, retained read-only for provenance. Do not
  branch from these. `master` was last touched 2025-08-06; `v0.69` 2026-02-17.
- **`v0.4` … `v0.21`** — release snapshots on lineage A. Archival only.
- **`feature/*`, `add-gene-archive-tests`, `refactor-coder-tempfile`,
  `claude/codebase-status-check-*`, `claude/go-mcts-ogs-guide-*`** — stale topic
  branches predating the unification.

## Pull requests

Pull requests #2 and #3 targeted `master` and had been open since August and November
2025 respectively. Because their base is on the retired lineage, retargeting them at
`main` would have produced a diff across unrelated histories rather than their actual
change. They were closed with an explanation; the branches remain, so the work can be
re-proposed against `main` if still wanted.

## One remaining manual step

The repository's **default branch must be switched to `main`** in
*Settings → Branches* on GitHub. That cannot be done through the API surface available
here. Until it is flipped, fresh clones will still land on `master`.
