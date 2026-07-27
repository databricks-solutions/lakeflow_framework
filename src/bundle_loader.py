# Compat shim — kept until v1.0.0.
# Use: from lakeflow_framework.bundle_loader import ...
from lakeflow_framework.bundle_loader import (  # noqa: F401
    Phase,
    register_bundle_sys_paths,
    run_init_scripts,
)
