# Compat shim — kept until v1.0.0.
# Use: from lakeflow_framework.secrets_manager import SecretsManager
from lakeflow_framework.secrets_manager import (  # noqa: F401
    SecretConfig,
    SecretValue,
    SecretsManager,
)
