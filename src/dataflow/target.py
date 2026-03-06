from __future__ import annotations

from typing import Any, ClassVar, Optional

import pipeline_config

from dataflow.field import Field


class TargetMeta(type):
    """
    Metaclass for :class:`Target` and its mixins.

    Responsibilities
    ----------------
    * Initialise ``_fields`` (list) and ``field_prefix`` (str) on every class
      that uses this metaclass **before** the class body runs, so that
      :class:`~dataflow.field.Field` descriptors have somewhere to register
      themselves via ``__set_name__``.
    * For concrete :class:`Target` subclasses (those that define
      ``target_type`` in their **own** namespace), validate required class
      attributes and register the class in :attr:`target_registry`.

    The registry is keyed by ``target_type`` value.  The auto-loader in
    ``dataflow/targets/__init__.py`` imports every ``.py`` file in that
    package, which triggers this registration automatically — no manual
    factory updates are required when adding a new target.
    """

    target_registry: dict[str, type[Target]] = {}

    _REQUIRED_CLS_ATTRS: tuple[str, ...] = ("target_type", "create_target")

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> TargetMeta:
        # Give Field descriptors a place to self-register BEFORE the class body
        # executes (i.e. before __set_name__ is called on each descriptor).
        namespace.setdefault("_fields", [])
        namespace.setdefault("field_prefix", "_field_")

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Is this a concrete Target subclass (not Target itself, not a mixin)?
        is_target_subclass = any(
            isinstance(base, TargetMeta) and issubclass(base, Target)  # noqa: F821
            for base in bases
            if base is not object
        )

        if is_target_subclass:
            for attr in mcs._REQUIRED_CLS_ATTRS:
                if not hasattr(cls, attr):
                    raise TypeError(
                        f"Target subclass '{name}' must define class attribute '{attr}'."
                    )
            # Register only classes that explicitly declare target_type in their
            # own namespace (inherited values are skipped, e.g. StagingTable).
            if "target_type" in namespace:
                existing = mcs.target_registry.get(namespace["target_type"])
                if existing is not None:
                    raise TypeError(
                        f"target_type {namespace['target_type']!r} is already registered "
                        f"by '{existing.__name__}'.  Each target must have a unique target_type."
                    )
                mcs.target_registry[namespace["target_type"]] = cls

        return cls

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_all_fields(cls: type) -> list[Field]:
        """
        Return all :class:`~dataflow.field.Field` instances across the MRO of
        *cls*, most-derived first (later MRO entries shadow earlier ones with
        the same Python attribute name).
        """
        seen: set[str] = set()
        result: list[Field] = []
        for klass in cls.__mro__:
            for f in klass.__dict__.get("_fields", []):
                if f.name not in seen:
                    seen.add(f.name)
                    result.append(f)
        return result


class Target(metaclass=TargetMeta):
    """
    Abstract base for all pipeline targets.

    Subclasses (or mixin compositions) declare:

    * ``target_type: ClassVar[str]``
        Unique string key; used to look up the class in the registry and
        matches the ``targetFormat`` value in the dataflow spec.
    * ``is_sink: ClassVar[bool]``
        ``True`` for sink-style targets (default ``False``).
    * ``creates_before_flows: ClassVar[bool]``
        ``True`` if the target must be created **before** flow groups are
        processed (e.g. streaming tables).  Materialized views set this to
        ``False`` so they are created after their input flows. Default ``True``.
    * :class:`~dataflow.field.Field` descriptors
        Declare the accepted spec kwargs, their mapping to JSON keys,
        required flags, and defaults.

    Construction
    ------------
    Direct (preferred when you know the concrete class)::

        StreamingTableDelta(table="my_table", ...)

    Factory dispatch via ``target_type`` (used by :class:`DataflowSpec`)::

        Target(target_type="streaming_table_delta", table="my_table")

    Adding a new target
    -------------------
    Drop a ``.py`` file into ``src/dataflow/targets/`` containing a class
    that inherits from ``Target`` (and any required mixins).  The auto-loader
    in ``targets/__init__.py`` will import it, and ``TargetMeta`` will
    register it automatically — no other changes required.
    """

    target_type: ClassVar[str]
    is_sink: ClassVar[bool] = False
    creates_before_flows: ClassVar[bool] = True
    _json_schema_constraints: ClassVar[dict] = {}

    # ---- universal spec field ----------------------------------------- #
    configFlags: list[str] = Field(required=False, default=[])

    # ---- transient (set at create() time, not from spec) -------------- #
    # Stored as plain instance attrs; not Field descriptors.
    _expectations: Optional[dict] = None
    _features: Any = None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __new__(cls, **kwargs: Any) -> Target:
        if cls is Target:
            target_type = kwargs.get("target_type")
            if target_type is None:
                raise TypeError(
                    "When constructing from Target base, "
                    "'target_type' is a required keyword argument."
                )
            target_cls = TargetMeta.target_registry.get(target_type)
            if target_cls is None:
                supported = ", ".join(sorted(TargetMeta.target_registry))
                raise ValueError(
                    f"Unknown target_type {target_type!r}. "
                    f"Supported types: {supported}"
                )
            return super().__new__(target_cls)
        return super().__new__(cls)

    def __init__(self, **kwargs: Any) -> None:
        # Discard factory-only key (present when called as Target(target_type=...)).
        kwargs.pop("target_type", None)
        # Write each kwarg directly into __dict__ using the Field storage-key
        # convention (prefix + spec_field).  This bypasses descriptor __set__
        # intentionally: we write to the exact storage location that Field.__get__
        # reads from, which is equivalent to calling __set__ but avoids double
        # dispatch and keeps unknown keys (not matched by any Field) harmless.
        fp = self.field_prefix
        for key, value in kwargs.items():
            self.__dict__[fp + key] = value
        self.__post_init__()

    def __post_init__(self) -> None:
        """Initialise pipeline-config handles.  Mixins extend this cooperatively."""
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.mandatory_table_properties = pipeline_config.get_mandatory_table_properties()
        self.operational_metadata_schema = pipeline_config.get_operational_metadata_schema()
        self.pipeline_details = pipeline_config.get_pipeline_details()
        self.substitution_manager = pipeline_config.get_substitution_manager()
        # Cooperative multiple-inheritance: let mixins chain their post-inits.
        parent = super()
        if hasattr(parent, "__post_init__"):
            parent.__post_init__()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @classmethod
    def get_spec_fields(cls) -> list[Field]:
        """All public :class:`~dataflow.field.Field` instances for this target.

        Fields whose ``spec_field`` starts with ``_`` are excluded as they are
        internal bookkeeping fields, not user-facing spec keys.
        """
        return [
            f for f in TargetMeta.get_all_fields(cls)
            if not (f.spec_field or "").startswith("_")
        ]

    @classmethod
    def get_required_spec_fields(cls) -> list[Field]:
        """Required public :class:`~dataflow.field.Field` instances (no default,
        ``required=True``)."""
        return [
            f for f in cls.get_spec_fields()
            if f.required and f.default is None
        ]

    @classmethod
    def to_json_schema(cls) -> dict:
        """Generate a JSON Schema ``object`` fragment for this target class.

        * Field types are inferred from Python type annotations via
          :func:`~dataflow.field._py_type_to_json_schema`.  An explicit
          ``json_type`` on the :class:`~dataflow.field.Field` takes priority.
        * Cross-field constraints (``oneOf``, ``anyOf``, ``allOf``) are
          collected from ``_json_schema_constraints`` across the entire MRO,
          base-to-derived, so subclasses can extend without repeating.
        """
        import typing
        hints = typing.get_type_hints(cls)
        properties: dict = {}
        required: list = []
        for f in cls.get_spec_fields():
            properties[f.spec_field] = f.to_json_schema(hints.get(f.name))
            if f.required and f.default is None:
                required.append(f.spec_field)

        schema: dict = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required

        # Merge _json_schema_constraints from base → derived (derived wins on
        # scalar keys; list keys like oneOf/anyOf/allOf are concatenated).
        for klass in reversed(cls.__mro__):
            constraints = klass.__dict__.get("_json_schema_constraints") or {}
            for key, val in constraints.items():
                if key in ("oneOf", "anyOf", "allOf") and key in schema:
                    val_list = val if isinstance(val, list) else [val]
                    schema[key] = schema[key] + val_list
                else:
                    schema[key] = val

        return schema

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def expectations(self) -> Optional[dict]:
        return self._expectations

    @property
    def features(self) -> Any:
        return self._features

    def create(
        self,
        expectations: Optional[dict] = None,
        features: Any = None,
    ) -> None:
        """Create the pipeline object (table, view, or sink) for this target.

        Args:
            expectations: Dict with ``expect_all`` / ``expect_all_or_drop`` /
                          ``expect_all_or_fail`` rule dicts.
            features:     :class:`~dataflow.features.Features` object carrying
                          optional feature flags (e.g. ``operationalMetadataEnabled``).
        """
        self._expectations = expectations
        self._features = features
        self.create_target_pre_hook()
        self.create_target()
        self.create_target_post_hook()

    def create_target_pre_hook(self) -> None:
        """Called before :meth:`create_target`.  Override in mixins / subclasses."""

    def create_target(self) -> None:
        """Override in concrete subclasses to register the table / sink / view."""

    def create_target_post_hook(self) -> None:
        """Called after :meth:`create_target`.  Override in mixins / subclasses."""
