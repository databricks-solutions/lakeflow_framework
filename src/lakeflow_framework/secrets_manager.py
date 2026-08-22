from dataclasses import dataclass
from typing import Dict, Pattern, Any, List
import re
import os

from pyspark.dbutils import DBUtils

import lakeflow_framework.pipeline_config as pipeline_config
import lakeflow_framework.utility as utility


@dataclass(frozen=True)
class SecretConfig:
    """
    Immutable configuration for a secret.
    
    Attributes:
        scope: The secret scope name
        key: The secret key name
        exceptionEnabled: Whether to raise exceptions on secret retrieval failure
    """
    scope: str
    key: str
    exceptionEnabled: bool = False

    def __post_init__(self):
        """Validate the secret configuration."""
        if not self.scope or not isinstance(self.scope, str):
            raise ValueError("Secret scope must be a non-empty string")
        if not self.key or not isinstance(self.key, str):
            raise ValueError("Secret key must be a non-empty string")

    def get_secret(self, dbutils: DBUtils) -> str:
        """Get the secret value, retrieving it if not already cached."""
        try:
            return SecretValue(
                dbutils.secrets.get(
                    scope=self.scope,
                    key=self.key
                )
            )
        except Exception as e:
            if self.exceptionEnabled:
                raise RuntimeError(
                    f"Failed to retrieve secret '{self.key}' from scope '{self.scope}': {str(e)}"
                ) from e
            return ""


class SecretValue:
    """
    Wrapper that yields the secret to Spark via ``str()`` while keeping
    ``repr()`` (used by dict logging and debug prints) redacted.
    """
    def __init__(self, secret: str, *, redacted: str = "[REDACTED]"):
        self.__secret = secret
        self.__redacted = redacted

    def __str__(self) -> str:
        """Return the secret value when converted to string (Spark options)."""
        return self.__secret

    def __repr__(self) -> str:
        """Return a redacted string representation for logs and debug prints."""
        return self.__redacted

    def __dict__(self) -> Dict[str, str]:
        """Prevent conversion to dict from exposing the secret value."""
        return {"secret": "[REDACTED]"}

    def __getstate__(self) -> Dict[str, str]:
        """Prevent pickling from exposing the secret value."""
        return {"secret": "[REDACTED]"}

    def clear(self) -> None:
        """Clear the cached secret value."""
        self.__secret = None


class SecretsManager:
    """
    This class provides a centralized way to manage secrets.
    
    Attributes:
        dbutils: DBUtils instance for accessing secrets
        logger: Logger instance for logging
        framework_secrets_config_path: Path to framework secrets config
        pipeline_secrets_config_path: Path to pipeline secrets config
        
    Example:
        manager = SecretsManager(dbutils, "./config/framework_secrets.json", "./config/pipeline_secrets.json")
        secrets = manager.get_secrets()  # Get all secrets
        value = manager.get_secret("db_password")  # Get specific secret
    """

    # Matches ``${secret.alias}`` anywhere in a string (whole value or embedded).
    SECRET_PATTERN: Pattern = re.compile(r"\$\{secret\.([a-zA-Z0-9_]+)\}")

    def __init__(
        self,
        json_validation_schema_path: str,
        framework_secrets_config_paths: List[str],
        pipeline_secrets_config_paths: List[str]
    ):
        self.dbutils = pipeline_config.get_dbutils()
        self.logger = pipeline_config.get_logger()
        self.json_validation_schema_path = json_validation_schema_path
        self.framework_secrets_config_paths = framework_secrets_config_paths
        self.pipeline_secrets_config_paths = pipeline_secrets_config_paths
        self.validator = utility.JSONValidator(json_validation_schema_path)

        # Load secret configurations only
        self._secret_configs = self._load_secrets()

    def _load_file(self, paths: List[str], config_type: str) -> Dict[str, Any]:
        """Load a single secret file from a list of possible paths."""
        existing_files = [path for path in paths if os.path.exists(path)]
        
        if len(existing_files) > 1:
            raise ValueError(f"Multiple {config_type} secrets files found. Only one is allowed: {existing_files}")
        
        if len(existing_files) == 1:
            file_path = existing_files[0]

            self.logger.info("Retrieving %s secrets from: %s", config_type, file_path)
            return utility.load_config_file_auto(file_path, False)
        
        self.logger.warning("No %s secrets file found.", config_type)
        return {}

    def _load_secrets_config_from_files(self) -> Dict[str, Any]:
        """Load and merge framework and pipeline secret configurations."""
        framework_secrets = self._load_file(self.framework_secrets_config_paths, "framework")
        pipeline_secrets = self._load_file(self.pipeline_secrets_config_paths, "pipeline")
        
        return utility.merge_dicts_recursively(pipeline_secrets, framework_secrets)

    def _load_secrets(self) -> Dict[str, SecretConfig]:
        """Load and merge framework and pipeline secret configurations."""
        json_data = self._load_secrets_config_from_files()
        errors = self.validator.validate(json_data)
        if errors:
            raise ValueError(f"Secrets validation errors: {errors}")

        try:
            return {
                alias: SecretConfig(**config)
                for alias, config
                in json_data.items()
            }
        except KeyError as e:
            raise ValueError(f"Invalid secret configuration: {e}") from e
        except TypeError as e:
            raise ValueError(f"Invalid secret configuration: {e}") from e
        except Exception as e:
            raise e

    def get_secret(self, alias: str) -> SecretValue:
        """
        Get a SecretValue object for a secret by its alias.
        
        Args:
            alias: The alias name of the secret
            
        Returns:
            A SecretValue object that will lazily retrieve the secret when accessed
        """
        if alias not in self._secret_configs:
            raise KeyError(f"Secret alias '{alias}' not found")
            
        return self._secret_configs[alias].get_secret(self.dbutils)

    def substitute_secrets(self, data: Any) -> Any:
        """
        Substitute ``${secret.alias}`` references with SecretValue objects.

        A field whose entire value is ``${secret.alias}`` is replaced by the
        secret wrapper. References embedded in a larger string (for example a
        Kafka JAAS config) are interpolated, and the result is still wrapped so
        ``repr()`` / dict logging stay redacted while ``str()`` yields the
        resolved value for Spark.

        Args:
            data: The data to process (dict, list, or any other type)

        Returns:
            Processed data with secret references replaced by SecretValue objects
        """
        def substitute_value(value: str) -> Any:
            matches = list(self.SECRET_PATTERN.finditer(value))
            if not matches:
                return value
            if len(matches) == 1 and matches[0].span() == (0, len(value)):
                return self.get_secret(matches[0].group(1))

            def replacer(match: re.Match[str]) -> str:
                return str(self.get_secret(match.group(1)))

            interpolated = self.SECRET_PATTERN.sub(replacer, value)
            redacted = self.SECRET_PATTERN.sub("[REDACTED]", value)
            return SecretValue(interpolated, redacted=redacted)

        if isinstance(data, dict):
            return {k: self.substitute_secrets(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.substitute_secrets(item) for item in data]
        elif isinstance(data, str):
            return substitute_value(data)
        else:
            return data
