# src/dataflow_spec/spec_type/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Union

import pipeline_config


class BaseSpecTransformer(ABC):
    """Base class for dataflow spec transformers."""
    
    def __init__(self):
        self.logger = pipeline_config.get_logger()

    @abstractmethod
    def _process_spec(self, spec_data: Dict) -> Union[Dict, List[Dict]]:
        """Transform the spec data. Returns either a single Dict or List[Dict]."""
        pass

    def transform(self, spec_data: Dict) -> Union[Dict, List[Dict]]:
        """Transform the spec data. Returns either a single Dict or List[Dict]."""
        spec_data = self._apply_features_and_limitations(spec_data)
        return self._process_spec(spec_data)
    
    def _apply_features_and_limitations(self, dataflow_spec: Dict) -> Dict:
        """Apply common features and limitations transformations."""
        # Operational MetadataSnapshot
        features = dataflow_spec.get("features", {})
        if not features:
            dataflow_spec["features"] = {}

        # FEATURE: Operational Metadata
        operational_metadata_enabled = features.get("operationalMetadataEnabled", True)
        dataflow_spec["features"]["operationalMetadataEnabled"] = operational_metadata_enabled

        # LIMITATIONS: CDC SNAPSHOT
        if dataflow_spec.get("cdcSnapshotSettings"):
            dataflow_spec["features"]["operationalMetadataEnabled"] = False

        return dataflow_spec
