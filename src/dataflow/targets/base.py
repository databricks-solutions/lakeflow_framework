from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Union, TypeVar
import os

from pyspark import pipelines as dp
import pyspark.sql.types as T

import pipeline_config
import utility

from ..enums import TableType, TargetConfigFlags
from ..features import Features

Self = TypeVar("Self", bound="BaseTargetDelta")


CONSTRAINT_KEY_WORDS = ("CONSTRAINT ", "PRIMARY KEY ", "FOREIGN KEY ")


@dataclass(kw_only=True)
class BaseTargetDelta():
    """
    Target details structure for Delta targets.

    Attributes:
        table (str): Table name.
        database (str, optional): Database name.
        type (str, optional): Type of table ["st", "mv"]. Defaults to "st".
        tableProperties (Dict, optional): Properties of the target table.
        partitionColumns (List[str], optional): List of partition columns.
        clusterByColumns (List[str], optional): List of cluster by columns.
        clusterByAuto (bool, optional): Whether to enable cluster by auto.
        schemaPath (str, optional): Path to the schema file (JSON or DDL format).
        tablePath (str, optional): Path to the Delta table.
        comment (str, optional): Comment for the target table.
        sparkConf (Dict, optional): Spark configuration for the target table.
        rowFilter (str, optional): Row filter for the target table.
        private (bool, optional): Whether the target table is private.

    Properties:
        schema_type (str): Type of schema ["json", "ddl"].
        schema (Union[Dict, str]): Schema structure.
        schema_json (Dict): Schema JSON.
        schema_struct (StructType): Schema structure.
        schema_ddl (str): Schema DDL.

    Methods:
        add_columns: Add columns to the target schema.
        remove_columns: Remove columns from the target schema.
        add_table_properties: Add table properties to the target details.
    """
    table: str
    database: Optional[str] = None
    type: str = "st"
    tableProperties: Dict = field(default_factory=dict)
    partitionColumns: List[str] = field(default_factory=list)
    clusterByColumns: List[str] = None #Must be passed as None as API expects None or a list with at least one column. [] causes an error
    clusterByAuto: bool = False
    schemaPath: Optional[str] = None
    tablePath: Optional[str] = None
    configFlags: List[str] = field(default_factory=list)
    comment: Optional[str] = None
    sparkConf: Optional[Dict] = None
    rowFilter: Optional[str] = None
    private: Optional[bool] = None
    _schema_type: str = None
    _schema_json: Dict = field(default_factory=dict)
    _schema_ddl: str = None
    _schema_struct: T.StructType = field(default=None, init=False)
    _schema_lines: List[str] = field(default_factory=list)
    _schema_constraints: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the target details and validate the configuration."""
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.mandatory_table_properties = pipeline_config.get_mandatory_table_properties()
        self.operational_metadata_schema = pipeline_config.get_operational_metadata_schema()
        self.pipeline_details = pipeline_config.get_pipeline_details()
        self.substitution_manager = pipeline_config.get_substitution_manager()

        self.tableProperties = utility.merge_dicts_recursively(
            self.mandatory_table_properties,
            self.tableProperties
        )
        if TargetConfigFlags.DISABLE_OPERATIONAL_METADATA in self.configFlags:
            self.operational_metadata_schema = None

        if self.database:
            self.table = f"{self.database}.{self.table}"

        # Validate table type
        self.type = self.type.lower()
        try:
            TableType(self.type)
        except ValueError as e:
            raise ValueError(
                f"Invalid table type: {self.type}. Must be one of {[t.value for t in TableType]}"
            ) from e

        # Validate partition and cluster columns
        if self.partitionColumns and self.clusterByColumns:
            raise ValueError("Cannot specify both partitionColumns and clusterByColumns")
        
        if self.partitionColumns and self.clusterByAuto:
            raise ValueError("Cannot specify partitionColumns and enable clusterByAuto")

        # Initialize schema if path is provided
        if self.schemaPath and self.schemaPath.strip() != "":
            self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Initialize the schema from the schema path."""
        # Get schema type
        file_extension = os.path.splitext(self.schemaPath)[1].lower()
        if file_extension not in ['.json', '.ddl']:
            raise ValueError(f"Unsupported schema file extension: {file_extension}. Only .json and .ddl are supported.")
        
        # Set schema type
        self._schema_type = file_extension[1:]

        # Get schema
        if file_extension == '.json':
            self._schema_json = utility.get_json_from_file(self.schemaPath)
            self._schema_struct = T.StructType.fromJson(self._schema_json)
            if not isinstance(self._schema_json, dict):
                raise ValueError(f"Invalid JSON schema format in {self.schemaPath}")
        elif file_extension == '.ddl':
            with open(self.schemaPath, 'r', encoding='utf-8') as f:
                self._schema_ddl = f.read()

                # Parse schema
                schema_lines = self._schema_ddl.split("\n")
                schema_lines = [line.strip().rstrip(",") for line in schema_lines]
                schema_lines = [line for line in schema_lines if not line.strip().startswith("--")]

                # Parse constraints
                schema_constraints = [line for line in schema_lines if line.strip().startswith(CONSTRAINT_KEY_WORDS)]
                schema_lines = [line for line in schema_lines if not line.strip().startswith(CONSTRAINT_KEY_WORDS)]
                
                self._schema_lines = schema_lines
                self._schema_constraints = schema_constraints

        # Initialize operational metadata schema
        if self.operational_metadata_schema:
            self.logger.info(f"Adding operational metadata schema to table: {self.table}")
            self._add_columns(self.operational_metadata_schema.fields)

    @property
    def schema_type(self) -> Optional[str]:
        """Get the schema type."""
        return self._schema_type

    @property
    def schema(self) -> Union[T.StructType, str]:
        """Get the schema."""
        if self._schema_type == "json":
            return self.schema_json
        elif self._schema_type == "ddl":
            return self.schema_ddl

    @property
    def schema_json(self) -> Dict:
        """Get the schema from the schema path."""
        return self._schema_struct.jsonValue()

    @property
    def schema_struct(self) -> T.StructType:
        """Get the schema struct from the schema path."""
        return self._schema_struct

    @property
    def schema_ddl(self) -> str:
        """Get the schema from the schema path."""
        schema_lines = self._schema_lines + self._schema_constraints
        return ",\n".join(schema_lines)

    def add_columns(self, columns: Union[List[T.StructField], List[Dict]]) -> Self:
        """
        Add columns to the target schema.

        Args:
            columns (Union[List[T.StructField], List[Dict]]): List of columns as StructFields or Dicts

        Returns:
            Self: The updated TargetDelta instance
        """
        self._add_columns(columns)
        return self

    def _add_columns(self, columns: Union[List[T.StructField], List[Dict]]):
        """Add columns to the target schema."""
        if not self._schema_struct and not self._schema_lines:
            raise ValueError(
                f"Attempting to add columns to table: {self.table} but schema structure is not initialized.")

        for column in columns:
            column = T.StructField.fromJson(column) if isinstance(column, dict) else column
            if not isinstance(column, T.StructField):
                raise ValueError(f"Unsupported column format: {type(column)}. Must be Dict or StructField.")

            if self.schema_type == "json":
                if column.name not in self._schema_struct.fieldNames():
                    self._schema_struct = self._schema_struct.add(column)
            elif self.schema_type == "ddl":
                if column.name not in self._schema_lines:
                    self._schema_lines.append(column.simpleString().replace(":", " "))

    def remove_columns(self, column_names: List[str]) -> Self:
        """
        Remove columns from the target schema.

        Args:
            column_names (List[str]): List of column names to remove.

        Returns:
            Self: The updated TargetDelta instance
        """
        self._remove_columns(column_names)
        return self
        
    def _remove_columns(self, column_names: List[str]):
        """Remove columns from the target schema."""
        if not self._schema_struct and not self._schema_lines:
            raise ValueError("Schema structure is not initialized.")

        if self.schema_type == "json":
            self._schema_struct = T.StructType([
                field for field in self._schema_struct.fields
                if field.name not in column_names
            ])
        elif self.schema_type == "ddl":
            self._schema_lines = [
                line for line in self._schema_lines
                if line.strip().split(" ")[0] not in column_names
            ]

    def add_table_properties(self, table_properties: Dict) -> Self:
        """
        Add table properties to the target details.

        Args:
            table_properties (Dict): Dictionary containing table properties to add.

        Returns:
            Self: The updated TargetDelta instance
        """
        self.tableProperties = utility.merge_dicts_recursively(self.tableProperties, table_properties)
        return self

    def create_table(
        self,
        expectations: Dict = None,
        features: Features = None
    ) -> None:
        """
        Create the target table for the data flow.

        Args:
            expectations: Optional dictionary containing:
                - expect_all: Rules that log violations
                - expect_all_or_drop: Rules that drop violating records
                - expect_all_or_fail: Rules that fail the pipeline on violations
        """
        logger = self.logger
        substitution_manager = self.substitution_manager

        logger.info(f"Creating Delta Table: {self.table}, Type: {self.type}")

        schema = None
        if self.schema_type == "json":
            schema = self.schema_struct
        elif self.schema_type == "ddl":
            if substitution_manager:
                schema = substitution_manager.substitute_string(self.schema)
        
        logger.debug(f"Schema Type: {self.schema_type}, Schema for {self.table}: {schema}")
        logger.debug(f"Expectations: {self.table}, {expectations}")
        logger.debug(f"Config Flags: {self.configFlags}")

        self._create_table(schema, expectations, features)

    @abstractmethod
    def _create_table(
        self,
        schema: T.StructType | str,
        expectations: Dict = None,
        features: Features = None
    ) -> None:
        """Abstract implementation for target specific table creation logic."""
        pass


class BaseSink(ABC):
    """Base class for all sink types.
    
    This abstract base class defines the interface that all sink implementations must follow.
    A sink represents a destination where data can be written to, such as Kafka topics,
    or Delta tables.

    Attributes:
        configFlags: List of config flags for the sink.

    Methods:
        create_sink: Create a sink with the specified name, type, and options.

    Properties:
        get_name (str): The unique identifier or name of the sink.
        get_type (str): The type of the sink (e.g., 'kafka', 'delta').
        get_options (Dict[str, Any]): Configuration options specific to the sink type.
    """
    configFlags: List[str] = []

    def __init__(self):
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.substitution_manager = pipeline_config.get_substitution_manager()

    @property
    @abstractmethod
    def sink_name(self) -> str:
        """Returns the name of the sink."""

    @property
    @abstractmethod
    def sink_type(self) -> str:
        """Returns the type of the sink."""

    @property
    @abstractmethod
    def sink_options(self) -> Dict[str, Any]:
        """Returns the options for the sink configuration."""

    def create_sink(self) -> None:
        """Create a sink with the specified name, type, and options."""
        logger = self.logger
        logger.info(f"Creating Sink: {self.sink_name}, Type: {self.sink_type}")
        logger.info(f"Sink Options: {self.sink_options}")
        dp.create_sink(f"`{self.sink_name}`", self.sink_type, self.sink_options)
