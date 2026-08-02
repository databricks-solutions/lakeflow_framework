"""
Quiet pre_init sample: record context once at load time (no event hooks).
"""

from __future__ import annotations

import pipeline_config
from utility import set_logger

logger = set_logger("BronzeSample")
_details = pipeline_config.get_pipeline_details()

logger.info(
    "pre_init: bundle context catalog=%s schema=%s layer=%s env=%s",
    _details.pipeline_catalog,
    _details.pipeline_schema,
    _details.pipeline_layer,
    _details.workspace_env,
)