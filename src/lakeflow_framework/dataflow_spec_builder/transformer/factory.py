from typing import List
from .base import BaseSpecTransformer
from .standard import StandardSpecTransformer
from .flow import FlowSpecTransformer
from .materialized_views import MaterializedViewSpecTransformer


class SpecTransformerFactory:
    """Factory for creating dataflow spec transformers."""
    
    _transformers = {
        "standard": StandardSpecTransformer,
        "flow": FlowSpecTransformer,
        "materialized_view": MaterializedViewSpecTransformer
    }
    
    @classmethod
    def create_transformer(cls, dataflow_type: str, dataflow_spec_mapping_path: str = None) -> BaseSpecTransformer:
        """Create appropriate transformer based on dataflow type."""
        transformer_class = cls._transformers.get(dataflow_type.lower())
        if not transformer_class:
            raise ValueError(f"Unknown dataflow type: {dataflow_type}")
        
        return transformer_class()
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Return list of supported dataflow types."""
        return list(cls._transformers.keys())