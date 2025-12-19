from abc import ABC
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
import os

import pyspark.sql.types as T

import pipeline_config
import utility


@dataclass
class SchemaMixin(ABC):
    """
    Mixin for schema retrieval and parsing.

    Attributes:
        schemaPath (str, optional): Path to the schema file (JSON or DDL format).

    Properties:
        schema_type (str): Type of schema ["json", "ddl"].
        schema (Union[Dict, str]): Schema structure.
        schema_json (Dict): Schema JSON.
        schema_struct (StructType): Schema structure.
        schema_ddl (str): Schema DDL.

    Methods:
        add_columns: Add columns to the target schema.
        remove_columns: Remove columns from the target schema.
    """
    schemaPath: Optional[str] = None
    _schema_type: Optional[str] = None
    _schema_json: Dict = field(default_factory=dict)
    _schema_ddl: str = field(default_factory=str)
    _schema_struct: T.StructType = field(default=None, init=False)
    _schema_lines: List[str] = field(default_factory=list)
    _schema_constraints: List[str] = field(default_factory=list)

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
            with open(self.schemaPath, 'r') as f:
                schema_ddl = f.read()
                substitution_manager = pipeline_config.get_substitution_manager()
                schema_ddl = substitution_manager.substitute_string(schema_ddl)
                self._schema_ddl = schema_ddl

                # Parse schema
                schema_lines = self._schema_ddl.split("\n")
                schema_lines = [line.strip().rstrip(",") for line in schema_lines]
                schema_lines = [line for line in schema_lines if not line.strip().startswith("--")]
                schema_constraints = [line for line in schema_lines if line.strip().startswith("CONSTRAINT ")]
                schema_lines = [line for line in schema_lines if not line.strip().startswith("CONSTRAINT ")]
                self._schema_lines = schema_lines
                self._schema_constraints = substitution_manager.substitute_string(schema_constraints)

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
 