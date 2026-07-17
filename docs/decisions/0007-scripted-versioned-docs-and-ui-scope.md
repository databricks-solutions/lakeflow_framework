# ADR-0007: Scripted versioned docs build and UI scope

**Date:** 2026-06-21  
**Status:** Accepted  
**PR:** docs/sphinx-versioning (includes commit `815b14a`)

---

## Context

We need stable, versioned Sphinx documentation published to GitHub Pages with:

1. Deterministic version selection rules.
2. A reproducible local + CI build path.
3. Predictable URL behavior (`<version>/index.html`) for local browsing and Pages hosting.
4. Minimal theme customization surface to reduce drift and maintenance.

An earlier `sphinx-multiversion` approach proved brittle in this repository environment.  
This branch moved to a script-driven build pipeline and then iterated on selector placement and styling.

## Decision

### 1) Use script-driven versioned docs builds (no `sphinx-multiversion`)

Adopt:

- `docs/scripts/build_versioned_docs.sh` (entrypoint)
- `docs/scripts/build_versioned_docs.py` (orchestrator)
- `docs/scripts/select_versions.py` (selection rules)

The pipeline builds:

- `main` as `current`
- selected release tags
- optional `local-branch-preview` (current branch) with `--preview`
- `docs/build/html/versions.json`
- root redirect `docs/build/html/index.html -> current/index.html`

Each published version (`current` and release tags) is built with **main's**
`docs/conf.py` + templates and that ref's `docs/source`, so the RTD version
selector stays available on historical docs. `--preview` adds
`local-branch-preview` using the current branch's own conf/source.

### 2) Shared superset `versions.json` + theme-native selectors

- Write one `versions.json` with both mike fields (`version`, `title`, `aliases`) and legacy RTD fields (`name`, `display_version`, `url`, …).
- RTD refs (`current` / tags, via main's conf) consume it at build time via `DOCS_VERSIONS_FILE` / `versions.html`.
- Immaterial preview refs enable `version_dropdown` and load the same file over HTTP.
- Do **not** use a feature-branch conf for historical tag builds — that drops the RTD selector on older tags.

### 3) Place docs tooling under `docs/scripts/`

Move build/selection scripts from `docs/` root into `docs/scripts/` and update all references in:

- `docs/Makefile`
- `.github/workflows/main-docs.yml`
- `docs/README.md`

This keeps docs root cleaner and maintains separation between runtime/package layout concerns and documentation build tooling.

## Consequences

- Local and CI now share the same explicit versioned build entrypoint.
- Version selection logic is testable and independent of theme internals.
- GitHub Pages artifact shape is deterministic and easy to reason about.
- Reduced template/CSS customization footprint lowers maintenance risk.
- Docs root is cleaner with scripting concerns grouped under `docs/scripts/`.

## Notes

- This ADR is specific to documentation build/deploy architecture and UI scope.
- It complements (does not replace) earlier ADRs focused on package/runtime architecture.
