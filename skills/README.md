# LFF Agent Skills

This directory holds [Agent Skills](https://agentskills.io/specification) for **end users of the Lakeflow Framework (LFF)**. Skills follow the open Agent Skills standard and work with AI coding assistants that support it — including **Cursor**, **Claude Code**, **Databricks Genie Code**, and others.

Each skill is a **self-contained folder** under `skills/<skill_name>/`: `SKILL.md` (agent entry point), human guides in `docs/`, agent reference in `references/`, plus `assets/`, `examples/`, and `scripts/`. Users install the whole folder into their assistant's skills directory.

The [Agent Skills](https://databricks-solutions.github.io/lakeflow_framework/ai-skills/index.html) section on the framework docs site is an **overview only** (one landing page per skill). It does not replace the skill package in the repository.

## Available Skills

| Skill | Folder | Description |
|-------|--------|-------------|
| **Data Flow Spec Builder** | [`dataflowspec_builder/`](./dataflowspec_builder/README.md) | Generates complete, production-ready Data Flow Spec pipeline bundles (specs, schemas, expectations, SQL/Python transforms, substitutions, templates, pipeline resource YAMLs, and `databricks.yml`) from natural language. Covers CDC (SCD1/2), data quality, quarantine, liquid clustering, multi-source streaming, table migration, and DABs deployment. |

## Using a Skill

Install the skill folder from this repository into your assistant's skills directory. Start with the skill's `README.md` and `docs/getting-started.md` for host-specific setup (Cursor, Claude Code, Genie Code, etc.).

## Adding a New Skill

When contributing a new end-user skill:

1. Create a new subfolder under `skills/` named after the skill (e.g. `skills/my_new_skill/`).
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`) and instructions for the agent.
3. Add a `README.md` documenting what the skill does and how to invoke it.
4. Register on the docs site (Option B — current): add a hub card and one toctree entry under `docs/source/ai-skills/index.rst`, symlink `index.md` → `skills/<skill>/README.md`, and optionally symlink `docs/*.md` for linkable guides (orphan pages — see `docs/conf.py`). Do **not** publish `references/` on the docs site; link pattern/schema rows in README to **Build** docs instead.
5. Add a new row to the **Available Skills** table above.

To simplify further (Option A), publish only the hub + skill README with no symlinked `docs/` pages — see `docs/source/contributors/dev-docs.rst`.
