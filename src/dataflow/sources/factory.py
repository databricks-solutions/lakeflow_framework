from typing import Dict, Type

from .base import BaseSource
from .batch_files import SourceBatchFiles
from .cloud_files import SourceCloudFiles
from .delta import SourceDelta
from .delta_join import SourceDeltaJoin
from .kafka import SourceKafka
from .python import SourcePython
from .sql import SourceSql
from ..enums import SourceType


class SourceFactory:
    """Factory for creating BaseSource instances."""

    # Registry of target types to their corresponding classes
    _source_registry: Dict[str, Type[BaseSource]] = {
        SourceType.BATCH_FILES: SourceBatchFiles,
        SourceType.CLOUD_FILES: SourceCloudFiles,
        SourceType.DELTA: SourceDelta,
        SourceType.DELTA_JOIN: SourceDeltaJoin,
        SourceType.KAFKA: SourceKafka,
        SourceType.PYTHON: SourcePython,
        SourceType.SQL: SourceSql
    }

    @classmethod
    def create(
        cls,
        source_type: str,
        source_details: Dict
    ) -> BaseSource:
        """
        Create a BaseSource instance based on the source type.

        Args:
            source_type: The type of source to create
            source_details: Configuration dictionary for the source

        Returns:
            BaseSource: An instance of the appropriate BaseSource class

        Raises:
            ValueError: If source_type is not supported
        """
        # Normalize source type
        source_type = source_type.lower()

        # Check if source type is supported
        if source_type not in cls._source_registry:
            supported = ", ".join(cls._source_registry.keys())
            raise ValueError(
                f'Unsupported source type "{source_type}". '
                f'Supported types are: {supported}'
            )

        # Get the appropriate source class
        source_class = cls._source_registry[source_type]

        # Create and return the source instance
        source = source_class(**source_details)

        return source

    @classmethod
    def register_source(
        cls,
        source_type: str,
        source_class: Type[BaseSource]
    ) -> None:
        """
        Register a new source type.

        Args:
            source_type: The identifier for the source type
            source_class: The class to instantiate for this source type

        Raises:
            ValueError: If source_type is already registered
        """
        if source_type in cls._source_registry:
            raise ValueError(f'Source type "{source_type}" is already registered')

        cls._source_registry[source_type] = source_class