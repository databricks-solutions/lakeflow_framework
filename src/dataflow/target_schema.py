"""
Dynamic generation of the target JSON Schema (replaces ``definitions_targets.json``).

The schema is built entirely from:

* :attr:`~dataflow.target.TargetMeta.target_registry` — auto-populated when
  ``dataflow.targets`` is imported (metaclass registration).
* :class:`~dataflow.field.Field` descriptors — provide field names, types,
  required status, patterns, enums, and nested schemas.
* ``_schema_constraints`` classvars — :class:`~dataflow.constraints.SchemaConstraint`
  instances for cross-field rules that cannot be expressed per-field.
* :class:`~dataflow.enums.TargetConfigFlags` — drives the ``configFlags``
  enum values so they stay in sync with the Python constant.

Usage
-----
Obtain the schema dict::

    from dataflow.target_schema import generate_target_schema
    schema = generate_target_schema()

The returned dict is injected into a :class:`jsonschema.RefResolver` store
so that ``$ref`` references to ``definitions_targets.json`` in the static
schema files are resolved from memory rather than from disk.
"""
from __future__ import annotations


def generate_target_schema() -> dict:
    """Build and return the full target schema dict.

    Triggers target auto-discovery (``import dataflow.targets``) so that every
    ``.py`` file in the ``targets/`` package is imported and registered before
    the schema is generated.
    """
    import dataflow.targets  # noqa: F401 — triggers TargetMeta registration
    from dataflow.target import TargetMeta
    from dataflow.enums import TargetConfigFlags

    config_flag_values = [
        v for k, v in vars(TargetConfigFlags).items()
        if not k.startswith("_") and isinstance(v, str)
    ]

    target_block: dict = {}
    oneOf_entries: list = []

    for target_type, cls in sorted(TargetMeta.target_registry.items()):
        key = f"target_{target_type}"   # e.g. "target_streaming_table_delta"
        target_block[key] = cls.to_json_schema()
        oneOf_entries.append({
            "properties": {
                "targetFormat": {"const": target_type},
                "targetDetails": {"$ref": f"#/target/{key}"},
            }
        })

    # Backward-compat legacy format aliases — old spec files continue to validate.
    oneOf_entries += _legacy_aliases()

    return {
        "title": "Target DataflowSpec Definitions",
        "targetFormat": {"oneOf": oneOf_entries},
        "target": target_block,
        "$defs": {
            "configFlags": {
                "type": "array",
                "items": {"type": "string", "enum": config_flag_values},
                "default": [],
            }
        },
    }


def _legacy_aliases() -> list:
    """Return backward-compat ``oneOf`` entries for retired ``targetFormat`` values.

    These map the old ``"delta"`` (with ``"type": "ST"/"MV"``) and
    ``"foreach_batch_sink"`` (with ``"type": "basic_sql"/"python_function"``)
    format names to the canonical generated schemas via ``$ref``, so existing
    spec files continue to pass JSON Schema validation without modification.
    """
    return [
        {
            # "targetFormat": "delta" with "type": "MV" → materialized_view_delta
            #                           with "type": "ST" (default) → streaming_table_delta
            "properties": {
                "targetFormat": {"const": "delta"},
                "targetDetails": {
                    "if":   {"properties": {"type": {"const": "MV"}}},
                    "then": {"$ref": "#/target/target_materialized_view_delta"},
                    "else": {"$ref": "#/target/target_streaming_table_delta"},
                },
            }
        },
        {
            # "targetFormat": "foreach_batch_sink" with "type": "basic_sql" → sql_foreach_batch_sink
            #                                      with "type": "python_function" → python_foreach_batch_sink
            "properties": {
                "targetFormat": {"const": "foreach_batch_sink"},
                "targetDetails": {
                    "if":   {"properties": {"type": {"const": "basic_sql"}}},
                    "then": {"$ref": "#/target/target_sql_foreach_batch_sink"},
                    "else": {"$ref": "#/target/target_python_foreach_batch_sink"},
                },
            }
        },
    ]
