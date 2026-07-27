# LFF Skills

This directory holds [Agent Skills](https://docs.databricks.com/aws/en/genie-code/skills) intended for **end users of the Lakeflow Framework (LFF)**. Each skill lives in its own subfolder and packages the instructions, reference docs, templates, and examples an agent needs to help you work with the framework from natural language.

## Available Skills

| Skill | Folder | Description |
|-------|--------|-------------|
| **Data Flow Spec Builder** | [`dataflowspec_builder/`](./dataflowspec_builder/README.md) | Generates complete, production-ready Data Flow Spec pipeline bundles (specs, schemas, expectations, SQL/Python transforms, substitutions, templates, pipeline resource YAMLs, and `databricks.yml`) from natural language. Covers CDC (SCD1/2), data quality, quarantine, liquid clustering, multi-source streaming, table migration, and DABs deployment. |

## Using a Skill

Each skill folder contains a `SKILL.md` (the entry point the agent loads) and a `README.md` with human-facing documentation. Start with the skill's own `README.md` for prompts, parameters, and examples.

## Adding a New Skill

When contributing a new end-user skill:

1. Create a new subfolder under `skills/` named after the skill (e.g. `skills/my_new_skill/`).
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`) and instructions for the agent.
3. Add a `README.md` documenting what the skill does and how to invoke it.
4. Add a new row to the **Available Skills** table above so this index stays current.
