# src/dataflow_spec/spec_type/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Union

import pipeline_config


class BaseSpecTransformer(ABC):
    """Base class for dataflow spec transformers."""

    # When True, transform() inspects the produced flow spec and warns on
    # source definitions that embed SQL/Python transformation logic. Spec
    # types that can already detect this on their own input (e.g. nodespec,
    # which distinguishes source nodes from transformation nodes) set this to
    # False and emit the warning themselves.
    WARN_INLINE_SOURCE_TRANSFORMATIONS_FROM_OUTPUT = True

    def __init__(self):
        self.logger = pipeline_config.get_logger()

    @abstractmethod
    def _process_spec(self, spec_data: Dict) -> Union[Dict, List[Dict]]:
        """Transform the spec data. Returns either a single Dict or List[Dict]."""
        pass

    def transform(self, spec_data: Dict) -> Union[Dict, List[Dict]]:
        """Transform the spec data. Returns either a single Dict or List[Dict]."""
        spec_data = self._apply_features_and_limitations(spec_data)
        result = self._process_spec(spec_data)
        if self.WARN_INLINE_SOURCE_TRANSFORMATIONS_FROM_OUTPUT:
            for flow_spec in (result if isinstance(result, list) else [result]):
                self._warn_inline_source_transformations(flow_spec)
        return result

    def _warn_inline_source_transformations(self, flow_spec: Dict) -> None:
        """Warn when a source definition embeds SQL/Python transformation logic.

        Defining a source whose type is SQL or Python (or appending the result
        of an inline SQL statement) folds transformation logic into the source
        definition. This is still supported for backward compatibility, but is
        discouraged: it conflates "where the data comes from" with "how the data
        is transformed". The recommended pattern is to declare a plain source
        and model transformation logic as a separate transformation step. This
        behaviour may not be supported in a future release.
        """
        if not isinstance(flow_spec, dict):
            return

        data_flow_id = flow_spec.get("dataFlowId")
        for flow_group in flow_spec.get("flowGroups", []) or []:
            flows = flow_group.get("flows", {}) or {}
            for flow_name, flow in flows.items():
                if str(flow.get("flowType", "")).lower() == "append_sql":
                    self.logger.warning(
                        "Flow '%s' (dataFlowId '%s') uses an inline SQL source "
                        "(flowType 'append_sql'). This is still supported but "
                        "discouraged and may not be supported in a future "
                        "release. Model transformation logic as a separate "
                        "transformation step instead.",
                        flow_name, data_flow_id,
                    )
                for view_name, view in (flow.get("views", {}) or {}).items():
                    source_type = str(view.get("sourceType", "")).lower()
                    if source_type in ("sql", "python"):
                        self.logger.warning(
                            "Source view '%s' (dataFlowId '%s') defines an "
                            "inline %s transformation (sourceType '%s'). This "
                            "is still supported but discouraged and may not be "
                            "supported in a future release. Declare a plain "
                            "source and model transformation logic as a "
                            "separate transformation step instead.",
                            view_name, data_flow_id, source_type, source_type,
                        )


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
