from typing import Dict, Type, Any

from .delta_materialized_view import TargetDeltaMaterializedView
from .delta_streaming_table import TargetDeltaStreamingTable
from .sink_delta import TargetDeltaSink
from .sink_kafka import TargetKafkaSink
from .sink_foreach_batch import TargetForEachBatchSink
from .sink_custom_python import TargetCustomPythonSink
from ..enums import TargetType, TableType

class TargetFactory:
    """Factory for creating BaseTarget instances."""

    # Registry of target types to their corresponding classes
    _registry: Dict[str, Dict[str, Type[Any]]] = {
        TargetType.DELTA: {
            TableType.MATERIALIZED_VIEW: TargetDeltaMaterializedView,
            TableType.STREAMING: TargetDeltaStreamingTable
        },
        TargetType.DELTA_SINK: {
            None: TargetDeltaSink
        },
        TargetType.KAFKA_SINK: {
            None: TargetKafkaSink
        },
        TargetType.FOREACH_BATCH_SINK: {
            None: TargetForEachBatchSink
        },
        TargetType.CUSTOM_PYTHON_SINK: {
            None: TargetCustomPythonSink
        }
    }

    @classmethod
    def create(
        cls,
        target_type: str,
        target_details: Dict
    ) -> Any:
        """
        Create a Target instance based on the target format.

        Args:
            target_type: The type of target to create
            target_details: Configuration dictionary for the target
        Returns:
            Any: An instance of the appropriate Target class

        Raises:
            ValueError: If target_type is not supported
        """
        # Normalize target format
        target_type = target_type.lower()

        if target_type not in cls._registry:
            supported = ", ".join(cls._registry.keys())
            raise ValueError(
                f'Unsupported target type "{target_type}". '
                f'Supported types are: {supported}'
            )

        target_subtypes = cls._registry[target_type]
        
        if target_type == TargetType.DELTA:
            table_type = target_details.get('type', None)
            if not table_type:
                raise ValueError("Table type must be specified for Delta targets")
            
            table_type = table_type.lower()
            if table_type not in target_subtypes:
                supported = ", ".join(target_subtypes.keys())
                raise ValueError(
                    f'Unsupported table type "{table_type}" for Delta target. '
                    f'Supported types are: {supported}'
                )
            
            target_class = target_subtypes[table_type]
        else:
            # For non-Delta targets, use the None key
            target_class = target_subtypes[None]

        return target_class(**target_details)
