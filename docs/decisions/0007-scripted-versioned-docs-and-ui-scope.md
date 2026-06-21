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
- `docs/build/html/versions.json`
- root redirect `docs/build/html/index.html -> current/index.html`

### 2) Keep selector UI scope minimal and theme-aligned

- Keep the RTD selector at the bottom (`docs/_templates/versions.html`).
- Keep breadcrumb version/release-date metadata (`docs/_templates/breadcrumbs.html`).
- Do **not** keep a second custom header selector path.

This limits ongoing CSS/template overrides and reduces regressions from theme changes.

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
