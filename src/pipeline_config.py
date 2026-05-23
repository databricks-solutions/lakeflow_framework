# Compat shim — kept until v1.0.0.
# Use: from lakeflow_framework import pipeline_config  or  from lakeflow_framework.pipeline_config import ...
from lakeflow_framework import pipeline_config  # noqa: F401
from lakeflow_framework.pipeline_config import *  # noqa: F401, F403
