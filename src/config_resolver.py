# Compat shim — kept until v1.0.0.
# Use: from lakeflow_framework.config_resolver import ...
from lakeflow_framework.config_resolver import (  # noqa: F401
    load_framework_default_json,
    load_framework_config,
    resolve_framework_config_dir,
    resolve_framework_config_path,
)
