from typing import Dict, Type

from ..enums import FlowType
from .base import BaseFlow
from .append_view import FlowAppendView
from .append_sql import FlowAppendSql
from .merge import FlowMerge
from .materialized_view import FlowMaterializedView

class FlowFactory:
    """Factory for creating Flow instances."""

    # Registry of target types to their corresponding classes
    _flow_registry: Dict[str, Type[BaseFlow]] = {
        FlowType.APPEND_SQL: FlowAppendSql,
        FlowType.APPEND_VIEW: FlowAppendView,
        FlowType.MERGE: FlowMerge,
        FlowType.MATERIALIZED_VIEW: FlowMaterializedView
    }

    @classmethod
    def create(
        cls,
        flow_name: str,
        flow_details: Dict
    ) -> BaseFlow:
        """
        Create a Flow instance based on the flow type.

        Args:
            flow_name: The name of the flow to create
            flow_details: Configuration dictionary for the flow

        Returns:
            BaseFlow: An instance of the appropriate BaseFlow class

        Raises:
            ValueError: If flow_type is not supported
        """
        flow_type = flow_details["flowType"].lower()

        # Check if flow type is supported
        if flow_type not in cls._flow_registry:
            supported = ", ".join(cls._flow_registry.keys())
            raise ValueError(
                f'Unsupported flow type "{flow_type}". '
                f'Supported formats are: {supported}'
            )

        # Get the appropriate flow class
        flow_class = cls._flow_registry[flow_type]

        # Create and return the flow instance
        flow = flow_class(flowName=flow_name, **flow_details)

        return flow
