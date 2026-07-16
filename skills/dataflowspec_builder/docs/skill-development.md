# Skill Development Guide

How to extend or customize this skill for your own use cases.

## Skill Structure

Genie Code Agent Skills follow a convention:

```
skill-directory/
├── SKILL.md          # Required — the skill definition Genie Code reads
├── assets/           # Optional — templates, configs, reference files
├── references/       # Optional — domain docs, schema references
├── scripts/          # Optional — automation scripts
└── examples/         # Optional — working examples for Genie Code to reference
```

The `SKILL.md` file is the core. Genie Code reads it to understand:
- **When** to activate the skill (trigger phrases)
- **What** to generate (schemas, templates, examples)
- **How** to generate it (workflow steps, constraints)

## Customizing for Your Domain

### 1. Update the Examples

Replace the energy-domain examples with your own:

```
examples/
├── your-bronze/
│   ├── dataflowspec/your_bronze_main.json
│   ├── schemas/your_table_schema.json
│   └── expectations/your_table_dqe.json
├── your-silver/
│   └── dataflowspec/your_silver_main.json
└── your-gold/
    └── dataflowspec/your_gold_main.json
```

### 2. Update the References

Edit `references/energy-domain-mapping.md` to describe your tables and their relationships:

```markdown
## Your Domain Tables

| Table | Description | Key | CDC Pattern |
|-------|------------|-----|-------------|
| raw_orders | Customer orders | order_id | SCD1 |
| raw_products | Product catalog | product_id | SCD2 |
```

### 3. Add Domain-Specific Expectations

Create expectation templates for your data quality rules:

```json
{
    "expect": [
        {"name": "valid_order_id", "constraint": "order_id IS NOT NULL", "tag": "completeness"},
        {"name": "positive_total", "constraint": "order_total > 0", "tag": "range"}
    ],
    "expect_or_drop": [
        {"name": "valid_status", "constraint": "status IN ('pending','shipped','delivered')", "tag": "validity"}
    ]
}
```

### 4. Update SKILL.md Triggers

Modify the "When to Use" section to include your domain terminology:

```markdown
## When to Use

- User says "generate a Data Flow Spec for orders"
- User needs CDC ingestion for the e-commerce data platform
- User asks for order-to-shipment pipeline using Data Flow Specs
```

## Adding New Patterns

To add support for a new pattern:

1. Create an example Data Flow Spec in `assets/dataflowspec-templates/`
2. Add the pattern to the "Patterns" section in `SKILL.md`
3. Add a corresponding example in `examples/`
4. Update `references/patterns-guide.md`

## Testing Your Skill

1. Upload the skill to `.assistant/skills/` on your workspace
2. Open a new notebook
3. Enter Genie Code Agent mode
4. Test with progressively complex prompts:
   - Start with: "What patterns does the dataflow-spec-builder support?"
   - Then: "Generate a simple bronze Data Flow Spec for my_table"
   - Then: "Create a complete medallion pipeline with templates and DQ"

## Tips for Effective Skills

- **Be specific in SKILL.md** — Include complete JSON schemas, not just descriptions
- **Include working examples** — Genie Code learns from examples in the skill directory
- **Use unique trigger phrases** — Avoid terms that overlap with built-in Databricks features
- **Add a "When NOT to Use" section** — Helps Genie Code avoid false positive activations
- **Keep the skill focused** — One skill per framework/pattern, not a catch-all
