"""
Declarative cross-field schema constraints for :class:`~dataflow.target.Target`.

Instead of writing raw JSON Schema dicts on target classes, declare
constraints using these types.  Each constraint knows how to:

* Serialise itself to a JSON Schema fragment via :meth:`SchemaConstraint.to_json_schema`
  (used by :meth:`~dataflow.target.Target.to_json_schema` for schema generation).
* Validate itself against a live instance via :meth:`SchemaConstraint.validate`
  (called by :meth:`~dataflow.target.Target._validate_constraints` during ``__post_init__``).

Usage on a target class::

    from dataflow.constraints import MutuallyExclusive, RequireOneOf

    class MyTarget(Target, DeltaMixin):
        _schema_constraints: ClassVar[list] = [
            MutuallyExclusive("clusterByColumns", "partitionColumns"),
            RequireOneOf("sourceView", "sqlPath", "sqlStatement"),
        ]

Multiple constraints from across the MRO are merged automatically by both
:meth:`~dataflow.target.Target.to_json_schema` and
:meth:`~dataflow.target.Target._validate_constraints`.
"""
from __future__ import annotations


class SchemaConstraint:
    """Abstract base for declarative cross-field constraints.

    Subclasses implement both :meth:`to_json_schema` (schema generation) and
    :meth:`validate` (runtime enforcement during ``__post_init__``).
    """

    def to_json_schema(self) -> dict:
        """Return the JSON Schema fragment that encodes this constraint."""
        raise NotImplementedError

    def validate(self, instance: object) -> None:
        """Raise :exc:`ValueError` if this constraint is violated on *instance*."""
        raise NotImplementedError


class MutuallyExclusive(SchemaConstraint):
    """Assert that the named fields cannot all be present simultaneously.

    Generates a ``oneOf`` rule that fails when every listed field is present
    at the same time, and raises :exc:`ValueError` at construction time when
    more than one field has a truthy value.

    Example::

        MutuallyExclusive("clusterByColumns", "partitionColumns")
        # JSON Schema → {"oneOf": [{"not": {"required": ["clusterByColumns", "partitionColumns"]}}]}
        # Runtime     → ValueError if both fields are set on the target instance
    """

    def __init__(self, *fields: str) -> None:
        if len(fields) < 2:
            raise ValueError(
                f"MutuallyExclusive requires at least 2 fields, got {len(fields)}."
            )
        self.fields: tuple[str, ...] = fields

    def to_json_schema(self) -> dict:
        return {"oneOf": [{"not": {"required": list(self.fields)}}]}

    def validate(self, instance: object) -> None:
        set_fields = [f for f in self.fields if getattr(instance, f, None)]
        if len(set_fields) > 1:
            names = " and ".join(f"'{f}'" for f in set_fields)
            raise ValueError(
                f"{type(instance).__name__}: {names} are mutually exclusive "
                "— set at most one."
            )


class RequireOneOf(SchemaConstraint):
    """Assert that at least one of the named fields must be present.

    Generates an ``anyOf`` rule where each branch requires exactly one of the
    listed fields, and raises :exc:`ValueError` at construction time when none
    of the fields has a truthy value.

    Example::

        RequireOneOf("sourceView", "sqlPath", "sqlStatement")
        # JSON Schema → {"anyOf": [{"required": ["sourceView"]}, ...]}
        # Runtime     → ValueError if none of the fields are set on the instance
    """

    def __init__(self, *fields: str) -> None:
        if len(fields) < 2:
            raise ValueError(
                f"RequireOneOf requires at least 2 fields, got {len(fields)}."
            )
        self.fields: tuple[str, ...] = fields

    def to_json_schema(self) -> dict:
        return {"anyOf": [{"required": [f]} for f in self.fields]}

    def validate(self, instance: object) -> None:
        if not any(getattr(instance, f, None) for f in self.fields):
            options = ", ".join(f"'{f}'" for f in self.fields)
            raise ValueError(
                f"{type(instance).__name__}: at least one of {options} must be provided."
            )
