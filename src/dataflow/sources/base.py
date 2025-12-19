from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import importlib.util
import os
from typing import Dict, List, Optional, TypeVar, Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
import pyspark.sql.types as T

from constants import MetaDataColumnDefs, SystemColumns
import pipeline_config
import utility

from ..enums import TargetConfigFlags
from ..features import Features
from ..operational_metadata import OperationalMetadataMixin
from ..sql import SqlMixin

Self = TypeVar("Self", bound="BaseSource")


@dataclass
class ReadConfig:
    """
    Configuration for reading data from a source.

    Attributes:
        features: feature flags.
        mode (str): The mode of reading (e.g., "stream" or "batch").
        quarantine_rules (str): The quarantine rules.
        uc_enabled (bool): Whether to use UC mode.
        target_config_flags (List[str]): The target config flags.
    """
    features: Features
    mode: str
    quarantine_rules: Optional[str] = None
    uc_enabled: Optional[bool] = True
    target_config_flags: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not isinstance(self.mode, str):
            raise ValueError("Mode must be a string")
        if self.mode not in ("stream", "batch"):
            raise ValueError("Mode must be either 'stream' or 'batch'")


@dataclass(kw_only=True)
class BaseSource(OperationalMetadataMixin, ABC):
    """
    Base class for all non-sql based source details implementations.

    Attributes:
        readerOptions (Dict, optional): Reader options.
        selectExp (List[str], optional): List of select expressions.
        whereClause (List[str], optional): List of WHERE clauses.
        pythonTransform (Dict, optional): Python transform configuration with:
            - functionPath (str): Path to Python file containing 'apply_transform' function
            - module (str): Module.function reference (e.g., 'transforms.apply_transform')
            - tokens (Dict): Token values to pass to the transform function

    Methods:
        add_reader_options(reader_options: Dict): Add or update reader options.
        get_df(mode: str) -> DataFrame: Get a DataFrame from the source details.
    """
    readerOptions: Optional[Dict[str, Any]] = field(default_factory=dict)
    selectExp: Optional[List[str]] = field(default_factory=list)
    whereClause: Optional[List[str]] = field(default_factory=list)
    pythonTransform: Optional[Dict[str, Any]] = field(default_factory=dict)
    

    def __post_init__(self) -> None:
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.substitution_manager = pipeline_config.get_substitution_manager()
        self.operational_metadata_schema = pipeline_config.get_operational_metadata_schema()
        self.pipeline_details = pipeline_config.get_pipeline_details()

    @abstractmethod
    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Get a DataFrame from the source details."""
        pass

    def add_reader_options(self, reader_options: Dict[str, Any]) -> Self:
        """Add or update reader options."""
        self.readerOptions.update(reader_options)
        return self

    def read_source(self, read_config: ReadConfig) -> DataFrame:
        """Get a DataFrame from the source details with applied transformations."""
        spark = self.spark
        logger = self.logger
        operational_metadata_schema = self.operational_metadata_schema
        pipeline_details = self.pipeline_details
        features = read_config.features
        target_config_flags = read_config.target_config_flags or []

        df = self._get_df(read_config)
        df = self._apply_python_function(df)
        df = self._apply_where_clause(df)
        df = self._apply_select_exp(df)

        # Drop cdf columns if present. Important as they are not allowed in the target table.
        # If data engineers need them they can alias them in the selectExp
        cdf_columns = [column.value for column in SystemColumns.CDFColumns]
        df = utility.drop_columns(df, cdf_columns)

        # Add operational metadata
        if (features.operationalMetadataEnabled 
            and self.operational_metadata_schema
            and TargetConfigFlags.DISABLE_OPERATIONAL_METADATA not in target_config_flags
        ):
            logger.debug("Adding operational metadata to DataFrame.")
            df = self._add_operational_metadata(
                spark,
                df,
                operational_metadata_schema,
                pipeline_details.__dict__
            )

        # Add quarantine flag
        quarantine_rules = read_config.quarantine_rules
        if quarantine_rules and quarantine_rules.strip():
            logger.debug("Adding quarantine flag to DataFrame.")
            df = df.withColumn(
                MetaDataColumnDefs.QUARANTINE_FLAG["name"],
                F.expr(quarantine_rules)
            )

        return df

    def _apply_where_clause(self, df: DataFrame) -> DataFrame:
        """Apply WHERE clauses to a DataFrame."""
        for clause in self.whereClause:
            if clause.strip():
                df = df.where(clause)
        return df

    def _apply_select_exp(self, df: DataFrame) -> DataFrame:
        """Apply SELECT expressions to a DataFrame."""
        return df.selectExpr(*self.selectExp) if self.selectExp else df

    def _apply_python_function(self, df: DataFrame) -> DataFrame:
        """
        Apply a custom Python transform function to a DataFrame if specified.
        
        Supports two methods via pythonTransform:
        - module: Import function from an extension module (recommended)
        - functionPath: Load function from a Python file
        
        The function signature depends on whether tokens are provided:
        - With tokens: apply_transform(df, tokens) -> DataFrame
        - Without tokens: apply_transform(df) -> DataFrame
        """
        if not self.pythonTransform:
            return df
        
        logger = self.logger
        function_path = self.pythonTransform.get("functionPath")
        module_ref = self.pythonTransform.get("module")
        tokens = self.pythonTransform.get("tokens", {})
        tokens = self.substitution_manager.substitute_dict(tokens)
        
        # Load the function from module or path
        if module_ref:
            logger.debug(f"Applying Python transform from module: {module_ref}")
            function = utility.load_python_function_from_module(module_ref)
        elif function_path:
            logger.debug(f"Applying Python transform from path: {function_path}")
            if not os.path.exists(function_path):
                raise FileNotFoundError(f"Python transform file not found: {function_path}")
            
            spec = importlib.util.spec_from_file_location("custom_transform", function_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load Python transform from: {function_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if not hasattr(module, 'apply_transform'):
                raise AttributeError(
                    f"Python transform file '{function_path}' must contain an 'apply_transform' function"
                )
            function = module.apply_transform
        else:
            raise ValueError("pythonTransform must specify either 'functionPath' or 'module'")
        
        # Apply the transformation
        if tokens:
            logger.debug(f"Applying transform with tokens: {tokens}")
            return function(df, tokens)
        return function(df)


@dataclass
class BaseSourceWithSchemaOnRead(BaseSource):
    """
    Base class for all non-sql based source details implementations that support schema on read.

    Attributes:
        readerOptions (Dict, optional): Reader options.
        selectExp (List[str], optional): List of select expressions.
        whereClause (List[str], optional): List of WHERE clauses.
        pythonTransform (Dict, optional): Python transform configuration.
        schemaPath (str, optional): Path to the schema file (JSON or DDL format).

    Properties:
        schema_json (Dict, optional): Schema JSON.
        schema_struct (StructType, optional): Schema struct.

    Methods:
        add_reader_options(reader_options: Dict): Add or update reader options.
        get_df(mode: str) -> DataFrame: Get a DataFrame from the source details.
    """
    schemaPath: str = None
    _schema_json: Dict[str, Any] = field(default_factory=dict, init=False)

    @property
    def schema_json(self) -> Dict[str, Any]:
        """Lazily load the schema JSON from the schema path."""
        if not self._schema_json and self.schemaPath and self.schemaPath.strip() != "":
            self._schema_json = utility.get_json_from_file(self.schemaPath)
        return self._schema_json

    @property
    def schema_struct(self) -> T.StructType:
        """Lazily load the schema from the schema path."""
        return T.StructType.fromJson(self.schema_json) if self.schema_json else None



@dataclass
class BaseSourceSql(SqlMixin, OperationalMetadataMixin, ABC):
    """
    Base class for all SQL based source details.

    Attributes:
        sqlPath (str): Path to the SQL file.
        sqlStatement (str): SQL statement to execute.

    Properties:
        rawSql (str): Lazily loaded raw SQL content from the SQL file.

    Methods:
        get_sql (str): SQL with substitutions applied.
        read_source(config: ReadConfig) -> DataFrame: Read the source using the provided configuration.
    """
    def __post_init__(self) -> None:
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.operational_metadata_schema = pipeline_config.get_operational_metadata_schema()
        self.pipeline_details = pipeline_config.get_pipeline_details()
        self.substitution_manager = pipeline_config.get_substitution_manager()

    def read_source(self, read_config: ReadConfig) -> DataFrame:
        """Read the source using the provided configuration."""
        df = self._get_df(read_config)
        spark = self.spark
        operational_metadata_schema = self.operational_metadata_schema
        pipeline_details = self.pipeline_details
        features = read_config.features
        target_config_flags = read_config.target_config_flags or []

        # Add operational metadata if needed
        if (features.operationalMetadataEnabled 
            and self.operational_metadata_schema
            and TargetConfigFlags.DISABLE_OPERATIONAL_METADATA not in target_config_flags
        ):
            df = self._add_operational_metadata(
                spark,
                df,
                operational_metadata_schema,
                pipeline_details.__dict__
            )

        # Add quarantine flag
        quarantine_rules = read_config.quarantine_rules
        if quarantine_rules and quarantine_rules.strip():
            df = df.withColumn(
                MetaDataColumnDefs.QUARANTINE_FLAG["name"],
                F.expr(quarantine_rules)
            )

        return df

    @abstractmethod
    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Get a DataFrame from the source details."""
        pass