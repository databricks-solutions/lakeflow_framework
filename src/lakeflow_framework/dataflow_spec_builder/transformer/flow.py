from typing import Dict

from .base import BaseSpecTransformer

class FlowSpecTransformer(BaseSpecTransformer):
    """Transform a flow dataflow specification."""

    def _process_spec(self, spec_data: Dict) -> Dict:
        """Transform a flow dataflow specification."""
        # Set the target table type
        target_format = spec_data.get("targetFormat")
        if target_format == "delta":
            spec_data["targetDetails"]["type"] = "st"

        return spec_data 