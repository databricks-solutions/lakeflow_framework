from dataclasses import dataclass, field
from typing import Any, Callable, Dict

from pyspark.sql import DataFrame
import pyspark.sql.functions as F

from constants import MetaDataColumnDefs, SystemColumns
import pipeline_config
import utility

from .base import ReadConfig
from ..operational_metadata import OperationalMetadataMixin


@dataclass(kw_only=True)
class SourcePython(OperationalMetadataMixin):
    """
    Source details for Python Function. 
    One of functionPath, pythonModule, or pythonFunction must be provided.
    
    - functionPath: Path to a Python file containing a 'get_df' function
    - pythonModule: Module.function reference (e.g., 'transforms.get_customer_data')
                   The module must be in the extensions directory (added to sys.path)
    - pythonFunction: Direct function reference (for internal framework use)

    Attributes:
        functionPath (str, optional): Path to the Python function file.
        pythonModule (str, optional): Module and function reference (e.g., 'module.function').
        pythonFunction (Callable, optional): Python function (internal use).
        tokens (Dict, optional): Tokens to be substituted in the Python function.

    Methods:
        read_source(config: ReadConfig) -> DataFrame: 
            Get a DataFrame from the source details with applied transformations.
    """
    functionPath: str = None
    pythonModule: str = None
    pythonFunction: Callable = None
    tokens: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.substitution_manager = pipeline_config.get_substitution_manager()
        self.pipeline_details = pipeline_config.get_pipeline_details()
        self.operational_metadata_schema = pipeline_config.get_operational_metadata_schema()

        self.tokens = self.substitution_manager.substitute_dict(self.tokens)

    def read_source(self, read_config: ReadConfig) -> DataFrame:
        """Read the source using the provided configuration."""
        spark = self.spark
        logger = self.logger
        pipeline_details = self.pipeline_details
        operational_metadata_schema = self.operational_metadata_schema

        logger.debug(f"Function Path: {self.functionPath}")
        logger.debug(f"Python Module: {self.pythonModule}")
        logger.debug(f"Tokens: {self.tokens}")
        logger.debug(f"Read Config: {read_config}")

        # Load the Python function from one of the available sources
        if self.pythonModule:
            # Load from extension module (e.g., 'transforms.get_customer_data')
            logger.debug(f"Loading Python function from module: {self.pythonModule}")
            function = utility.load_python_function_from_module(
                self.pythonModule,
                ["spark", "tokens"]
            )
        elif self.functionPath:
            # Load from file path
            function = utility.load_python_function(
                self.functionPath,
                "get_df",
                ["spark", "tokens"]
            )
        elif self.pythonFunction:
            # Direct function reference (internal use)
            function = self.pythonFunction
        else:
            raise ValueError(
                "One of pythonModule or functionPath must be provided"
            )

        # Get the DataFrame
        df = function(spark, self.tokens)

        # Drop cdf columns if present. Important as they are not allowed in the target table.
        # If data engineers need them they can alias them in the selectExp
        cdf_columns = [column.value for column in SystemColumns.CDFColumns]
        df = utility.drop_columns(df, cdf_columns)

        # Add operational metadata if schema is provided
        operational_metadata_enabled = read_config.features.operationalMetadataEnabled
        if operational_metadata_enabled and operational_metadata_schema:
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
