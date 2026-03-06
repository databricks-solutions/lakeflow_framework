from __future__ import annotations

import os
from typing import ClassVar, Optional, Union

import pyspark.sql.types as T

import utility
from dataflow.constraints import MutuallyExclusive
from dataflow.enums import TargetConfigFlags
from dataflow.field import Field
from dataflow.target import TargetMeta

CONSTRAINT_KEYWORDS = ("CONSTRAINT ", "PRIMARY KEY ", "FOREIGN KEY ")


class DeltaMixin(metaclass=TargetMeta):
    """
    Mixin that adds Delta-table handling to a :class:`~dataflow.target.Target`
    subclass.

    Declares all spec fields common to Delta-backed tables (streaming tables
    and materialized views), manages schema loading from ``.json`` / ``.ddl``
    files, merges mandatory table properties, and resolves the final schema
    string/struct in :meth:`create_target_pre_hook` so that
    :meth:`create_target` implementations can consume ``self._table_schema``
    directly.

    Spec fields (``targetDetails`` keys)
    ------------------------------------
    * ``table``             — target table name (required)
    * ``database``          — optional database prefix
    * ``tableProperties``   — dict of Spark table properties
    * ``partitionColumns``  — list of partition column names
    * ``clusterByColumns``  — list of liquid-clustering column names
                               (mutually exclusive with partitionColumns)
    * ``clusterByAuto``     — enable automatic liquid clustering
    * ``schemaPath``        — path to a ``.json`` or ``.ddl`` schema file
    * ``tablePath``         — external Delta table path
    * ``comment``           — table comment
    * ``sparkConf``         — Spark configuration dict
    * ``rowFilter``         — row-level security filter expression
    * ``private``           — mark table as private in the pipeline
    * ``configFlags``       — list of :class:`~dataflow.enums.TargetConfigFlags`
                               (inherited from :class:`~dataflow.target.Target`)
    """

    _schema_constraints: ClassVar[list] = [
        MutuallyExclusive("clusterByColumns", "partitionColumns"),
    ]

    # ---- spec fields -------------------------------------------------- #
    target_name: str = Field(spec_field="table")
    database: Optional[str] = Field(required=False)
    tableProperties: dict = Field(default={})
    partitionColumns: list[str] = Field(default=[])
    # Must stay None (not []) when unset — the DLT API rejects an empty list.
    clusterByColumns: Optional[list[str]] = Field(required=False)
    clusterByAuto: bool = Field(required=False, default=False)
    schemaPath: Optional[str] = Field(required=False, pattern=r"\.(json|ddl)$")
    tablePath: Optional[str] = Field(required=False)
    comment: Optional[str] = Field(required=False)
    sparkConf: Optional[dict] = Field(required=False)
    rowFilter: Optional[str] = Field(required=False)
    private: Optional[bool] = Field(required=False)

    # ------------------------------------------------------------------
    # Post-init (cooperative MI)
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        # Initialise private schema state as plain instance attributes.
        # These are NOT Field descriptors — they represent internal mutable
        # state that is never loaded from the spec.
        self._schema_type: Optional[str] = None
        self._schema_struct: Optional[T.StructType] = None
        self._schema_ddl: Optional[str] = None
        self._schema_lines: list[str] = []
        self._ddl_constraints: list[str] = []
        self._table_schema: Optional[Union[T.StructType, str]] = None

        # Allow parent/sibling post-inits to run first (cooperative MI).
        if hasattr(super(), "__post_init__"):
            super().__post_init__()

        # Merge mandatory table properties declared in pipeline config.
        self.tableProperties = utility.merge_dicts_recursively(
            self.mandatory_table_properties,
            self.tableProperties,
        )

        # Respect the disable-operational-metadata config flag.
        if TargetConfigFlags.DISABLE_OPERATIONAL_METADATA in self.configFlags:
            self.operational_metadata_schema = None

        # Qualify the table name with the database prefix if provided.
        if self.database:
            self.target_name = f"{self.database}.{self.target_name}"

        # Validate mutually exclusive cluster/partition options.
        if self.partitionColumns and self.clusterByAuto:
            raise ValueError(
                f"'{self.target_name}': partitionColumns and clusterByAuto are "
                "mutually exclusive."
            )

        # Load schema from file if a path was given.
        if self.schemaPath and self.schemaPath.strip():
            self._initialize_schema()

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def _initialize_schema(self) -> None:
        ext = os.path.splitext(self.schemaPath)[1].lower()
        if ext not in (".json", ".ddl"):
            raise ValueError(
                f"Unsupported schema file extension {ext!r} for "
                f"'{self.target_name}'.  Only .json and .ddl are supported."
            )
        self._schema_type = ext[1:]

        if ext == ".json":
            schema_json = utility.get_json_from_file(self.schemaPath)
            if not isinstance(schema_json, dict):
                raise ValueError(
                    f"Invalid JSON schema in {self.schemaPath!r} for '{self.target_name}'."
                )
            self._schema_struct = T.StructType.fromJson(schema_json)
        else:  # .ddl
            with open(self.schemaPath, "r", encoding="utf-8") as fh:
                self._schema_ddl = fh.read()
            lines = [ln.strip().rstrip(",") for ln in self._schema_ddl.split("\n")]
            lines = [ln for ln in lines if not ln.startswith("--")]
            self._ddl_constraints = [
                ln for ln in lines if ln.startswith(CONSTRAINT_KEYWORDS)
            ]
            self._schema_lines = [
                ln for ln in lines if not ln.startswith(CONSTRAINT_KEYWORDS)
            ]

        if self.operational_metadata_schema:
            self.logger.info(
                f"Adding operational metadata columns to: {self.target_name}"
            )
            self._add_columns(self.operational_metadata_schema.fields)

    @property
    def schema_type(self) -> Optional[str]:
        """Schema format: ``'json'``, ``'ddl'``, or ``None``."""
        return self._schema_type

    @property
    def schema(self) -> Optional[Union[dict, str]]:
        """Schema as a JSON dict (for ``.json``) or DDL string (for ``.ddl``)."""
        if self._schema_type == "json":
            return self.schema_json
        if self._schema_type == "ddl":
            return self.schema_ddl
        return None

    @property
    def schema_json(self) -> Optional[dict]:
        """Schema as a JSON-serialisable dict, or ``None`` if not loaded."""
        return self._schema_struct.jsonValue() if self._schema_struct else None

    @property
    def schema_struct(self) -> Optional[T.StructType]:
        """Schema as a :class:`pyspark.sql.types.StructType`, or ``None``."""
        return self._schema_struct

    @property
    def schema_ddl(self) -> Optional[str]:
        """Schema as a DDL string (column definitions + constraints), or ``None``."""
        if not self._schema_lines and not self._ddl_constraints:
            return None
        return ",\n".join(self._schema_lines + self._ddl_constraints)

    # ---- backward-compatibility alias --------------------------------- #

    @property
    def table(self) -> str:
        """Alias for :attr:`target_name` (backward compatibility)."""
        return self.target_name

    # ------------------------------------------------------------------
    # Column helpers
    # ------------------------------------------------------------------

    def _add_columns(self, columns: list[Union[T.StructField, dict]]) -> None:
        if not self._schema_struct and not self._schema_lines:
            raise ValueError(
                f"Cannot add columns to '{self.target_name}': "
                "schema has not been initialised."
            )
        for col in columns:
            if isinstance(col, dict):
                col = T.StructField.fromJson(col)
            if not isinstance(col, T.StructField):
                raise TypeError(
                    f"Expected StructField or dict, got {type(col).__name__}."
                )
            if self._schema_type == "json":
                if col.name not in self._schema_struct.fieldNames():
                    self._schema_struct = self._schema_struct.add(col)
            elif self._schema_type == "ddl":
                if col.name not in self._schema_lines:
                    self._schema_lines.append(col.simpleString().replace(":", " "))

    def add_columns(
        self, columns: list[Union[T.StructField, dict]]
    ) -> DeltaMixin:
        """Add *columns* to the schema.  Returns ``self`` for chaining."""
        self._add_columns(columns)
        return self

    def remove_columns(self, column_names: list[str]) -> DeltaMixin:
        """Remove *column_names* from the schema.  Returns ``self`` for chaining."""
        if not self._schema_struct and not self._schema_lines:
            raise ValueError(
                f"Cannot remove columns from '{self.target_name}': "
                "schema has not been initialised."
            )
        if self._schema_type == "json":
            self._schema_struct = T.StructType(
                [f for f in self._schema_struct.fields if f.name not in column_names]
            )
        elif self._schema_type == "ddl":
            self._schema_lines = [
                ln for ln in self._schema_lines
                if ln.strip().split(" ")[0] not in column_names
            ]
        return self

    def add_table_properties(self, props: dict) -> DeltaMixin:
        """Merge *props* into table properties.  Returns ``self`` for chaining."""
        self.tableProperties = utility.merge_dicts_recursively(
            self.tableProperties, props
        )
        return self

    # ------------------------------------------------------------------
    # Pre-hook: resolve schema once before create_target runs
    # ------------------------------------------------------------------

    def create_target_pre_hook(self) -> None:
        if hasattr(super(), "create_target_pre_hook"):
            super().create_target_pre_hook()

        sm = self.substitution_manager
        schema: Optional[Union[T.StructType, str]] = None

        if self._schema_type == "json":
            schema = self._schema_struct
        elif self._schema_type == "ddl":
            raw = self.schema_ddl
            schema = sm.substitute_string(raw) if sm else raw

        self._table_schema = schema

        self.logger.info(f"Creating Delta table '{self.target_name}'")
        self.logger.debug(
            f"schema_type={self._schema_type!r}, "
            f"expectations={self._expectations!r}, "
            f"configFlags={self.configFlags!r}"
        )
