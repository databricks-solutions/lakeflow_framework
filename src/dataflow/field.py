from __future__ import annotations

from typing import Any, Optional, Union


# ---------------------------------------------------------------------------
# JSON Schema type-inference helpers
# ---------------------------------------------------------------------------

_JSON_TYPE_MAP: dict[type, str] = {
    str:   "string",
    int:   "integer",
    float: "number",
    bool:  "boolean",
    dict:  "object",
}


def _py_type_to_json_schema(annotation: Any) -> tuple[Optional[str], Optional[dict]]:
    """Return ``(json_type, items_schema)`` inferred from a Python type annotation.

    Handles ``Optional[X]`` (unwrapped to ``X``), ``list[X]`` / ``List[X]``,
    and plain scalar types.  Returns ``(None, None)`` for anything it cannot
    map, so callers can fall back gracefully.
    """
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())

    # Optional[X]  →  Union[X, None]
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _py_type_to_json_schema(non_none[0])
        return None, None

    # list[X] / List[X]
    if origin is list:
        item_type = args[0] if args else None
        items = {"type": _JSON_TYPE_MAP[item_type]} if item_type in _JSON_TYPE_MAP else {}
        return "array", items

    return _JSON_TYPE_MAP.get(annotation), None


# ---------------------------------------------------------------------------
# Field descriptor
# ---------------------------------------------------------------------------

class Field:
    """
    Descriptor for Target spec fields.

    Maps between a Python attribute name and the JSON spec key, stores the
    value per-instance in ``instance.__dict__``, and exposes metadata used
    for introspection (required/optional, defaults, JSON Schema generation).

    Args:
        spec_field:   The JSON spec key.  Defaults to the Python attribute name
                      when omitted (set by ``__set_name__``).
        required:     When ``True`` and no ``default`` is given the field is
                      considered mandatory in the spec.
        default:      Default value returned when the field has not been set.
                      Mutable defaults (``dict``, ``list``) are **copied**
                      per-instance to prevent accidental shared state.
        json_type:    Explicit JSON Schema type string (``"string"``,
                      ``"object"``, ``"array"``, ``"boolean"`` …).  When
                      omitted the type is inferred from the Python annotation
                      at schema-generation time.
        enum:         List of allowed values (emitted as ``"enum": [...]``).
        pattern:      Regex pattern for string fields.
        items:        JSON Schema for array items, e.g. ``{"type": "string"}``.
        schema_extra: Raw dict merged last into the generated fragment —
                      escape hatch for nested ``properties``, ``required``,
                      or any other complex constraint.

    Usage::

        class MyTarget(Target, SomeMixin):
            table_name: str = Field(spec_field="table")
            comment: Optional[str] = Field(required=False)
            opts: dict = Field(default={})
            schema_path: Optional[str] = Field(
                required=False,
                pattern=r"\\.(json|ddl)$",
            )

    The storage key in ``instance.__dict__`` is ``field_prefix + spec_field``
    (e.g. ``"_field_table"``).  ``field_prefix`` is set on the owning class by
    :class:`TargetMeta` before any ``__set_name__`` calls run.
    """

    def __init__(
        self,
        spec_field: Optional[str] = None,
        required: bool = True,
        default: Any = None,
        # JSON Schema metadata
        json_type: Optional[str] = None,
        enum: Optional[list] = None,
        pattern: Optional[str] = None,
        items: Optional[dict] = None,
        schema_extra: Optional[dict] = None,
    ) -> None:
        self.name: Optional[str] = None       # Python attribute name (set by __set_name__)
        self.spec_field: Optional[str] = spec_field
        self.required: bool = required
        self.default: Any = default
        self._prefix: str = "_field_"         # may be overridden by __set_name__
        # Schema metadata
        self.json_type = json_type
        self.enum = enum
        self.pattern = pattern
        self.items = items
        self.schema_extra = schema_extra

    # ------------------------------------------------------------------
    # Descriptor protocol
    # ------------------------------------------------------------------

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        if self.spec_field is None:
            self.spec_field = name
        # Inherit the storage prefix declared by TargetMeta on the owner class.
        if hasattr(owner, "field_prefix"):
            self._prefix = owner.field_prefix
        # Self-register so TargetMeta.get_all_fields() can discover this descriptor.
        owner._fields.append(self)

    def _key(self) -> str:
        """Return the storage key used in ``instance.__dict__``."""
        return self._prefix + self.spec_field

    def __set__(self, instance: Any, value: Any) -> None:
        instance.__dict__[self._key()] = value

    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        key = self._key()
        if key in instance.__dict__:
            return instance.__dict__[key]
        # Return a fresh copy of mutable defaults to prevent shared state.
        if isinstance(self.default, dict):
            instance.__dict__[key] = {}
            return instance.__dict__[key]
        if isinstance(self.default, list):
            instance.__dict__[key] = []
            return instance.__dict__[key]
        return self.default

    def __delete__(self, instance: Any) -> None:
        instance.__dict__.pop(self._key(), None)

    # ------------------------------------------------------------------
    # JSON Schema generation
    # ------------------------------------------------------------------

    def to_json_schema(self, annotation: Any = None) -> dict:
        """Return a JSON Schema fragment for this field.

        Type information is resolved in priority order:

        1. ``json_type`` explicitly set on this ``Field``.
        2. Inferred from *annotation* (the Python type hint for this attribute).
        3. Omitted if neither is available.

        Any ``schema_extra`` dict is merged last, allowing arbitrary overrides
        or additions (e.g. nested ``properties`` for an ``"object"`` field).
        """
        json_type = self.json_type
        items = self.items
        if json_type is None and annotation is not None:
            json_type, items = _py_type_to_json_schema(annotation)

        schema: dict = {}
        if json_type:
            schema["type"] = json_type
        if self.enum is not None:
            schema["enum"] = self.enum
        if self.pattern is not None:
            schema["pattern"] = self.pattern
        if items is not None:
            schema["items"] = items
        if self.schema_extra:
            schema.update(self.schema_extra)
        return schema

    def __repr__(self) -> str:
        return (
            f"Field(name={self.name!r}, spec_field={self.spec_field!r}, "
            f"required={self.required})"
        )
