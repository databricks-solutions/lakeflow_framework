from dataclasses import dataclass, field
from typing import Dict, List, Union, Optional

from pyspark import pipelines as dp
from pyspark.sql import DataFrame

import pipeline_config

from .dataflow_config import DataFlowConfig
from .enums import SourceType
from .sources import SourceFactory, ReadConfig


@dataclass
class ViewConfig:
    """View configuration.

    Attributes:
        target_config_flags: The target config flags.
    """
    target_config_flags: Optional[List[str]] = None


@dataclass
class View:
    """
    View definition structure.

    Attributes:
        viewName (str): Name of the view.
        mode (str): Execution mode.
        sourceType (str): Type of source.
        sourceDetails (Dict): Source details.

    Properties:
        isCdfEnabled (bool): Flag indicating if CDF is enabled for Delta sources.

    Methods:
        add_reader_options(reader_options: Dict): Add or update reader options.
        get_source_details(): Get source details based on source type.
    """
    viewName: str
    mode: str
    sourceType: str
    sourceDetails: Union[Dict, List]
    _config: ReadConfig = None

    def __post_init__(self):
        self.mode = self.mode.lower()
        self.sourceType = self.sourceType.lower()
        self.read_config = None

    @property
    def isCdfEnabled(self):
        """Check if CDF is enabled for Delta sources."""
        cdf_enabled = False
        if self.sourceType == SourceType.DELTA:
            cdf_enabled = self.sourceDetails["cdfEnabled"] \
                if "cdfEnabled" in self.sourceDetails else False
        return cdf_enabled

    def add_reader_options(self, reader_options: Dict):
        """Add or update reader options."""
        if "readerOptions" in self.sourceDetails:
            self.sourceDetails["readerOptions"].update(reader_options)
        else:
            self.sourceDetails["readerOptions"] = reader_options

    def create_view(
        self,
        dataflow_config: DataFlowConfig,
        view_config: Optional[ViewConfig] = None,
        quarantine_rules: Optional[str] = None
    ):
        """Create the View"""
        self.read_config = ReadConfig(
            features=dataflow_config.features,
            mode=self.mode,
            quarantine_rules=quarantine_rules,
            uc_enabled=dataflow_config.uc_enabled,
            target_config_flags=view_config.target_config_flags if view_config else None
        )
        logger = pipeline_config.get_logger()
        logger.info("Creating View: %s, mode: %s, source type: %s", self.viewName, self.mode , self.sourceType)

        dp.view(
            self._get_df,
            name=self.viewName,
            comment=f"input dataset view for {self.viewName}",
        )

    def get_source_details(self):
        """Get the views source details based on source type."""
        return SourceFactory.create(self.sourceType, self.sourceDetails)

    def _get_df(self) -> DataFrame:
        """Retrieve the DataFrame based on the configured source type."""
        return self.get_source_details().read_source(self.read_config)
