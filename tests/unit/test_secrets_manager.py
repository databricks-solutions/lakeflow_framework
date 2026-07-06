"""Unit tests for secrets_manager.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from secrets_manager import SecretConfig, SecretValue, SecretsManager


class TestSecretConfig:
    def test_validates_scope_and_key(self):
        with pytest.raises(ValueError, match="scope"):
            SecretConfig(scope="", key="k")

    def test_get_secret_returns_secret_value(self):
        dbutils = MagicMock()
        dbutils.secrets.get.return_value = "s3cr3t"
        config = SecretConfig(scope="scope", key="key")
        value = config.get_secret(dbutils)
        assert str(value) == "s3cr3t"

    def test_get_secret_returns_empty_when_disabled_and_lookup_fails(self):
        dbutils = MagicMock()
        dbutils.secrets.get.side_effect = RuntimeError("not found")
        config = SecretConfig(scope="scope", key="key", exceptionEnabled=False)
        assert config.get_secret(dbutils) == ""


class TestSecretValue:
    def test_repr_is_redacted(self):
        assert repr(SecretValue("hidden")) == "[REDACTED]"


class TestSecretsManager:
    def test_loads_and_merges_framework_and_pipeline_secrets(
        self, tmp_path: Path, pipeline_context, framework_src_path, fixtures_dir: Path
    ):
        schema = str(framework_src_path / "schemas" / "secrets.json")
        fw = tmp_path / "fw_secrets.json"
        pl = tmp_path / "pl_secrets.json"
        fw.write_text((fixtures_dir / "specs" / "framework_secrets.json").read_text())
        pl.write_text((fixtures_dir / "specs" / "pipeline_secrets.json").read_text())

        mgr = SecretsManager(schema, [str(fw)], [str(pl)])
        assert "db_password" in mgr._secret_configs
        assert "api_key" in mgr._secret_configs

    def test_get_secret_raises_for_unknown_alias(self, secrets_manager):
        with pytest.raises(KeyError, match="not found"):
            secrets_manager.get_secret("missing_alias")

    def test_substitute_secrets_with_configured_alias(
        self, tmp_path: Path, pipeline_context, framework_src_path
    ):
        schema = str(framework_src_path / "schemas" / "secrets.json")
        secrets_file = tmp_path / "secrets.json"
        empty_pipeline = tmp_path / "empty.json"
        secrets_file.write_text('{"db_password": {"scope": "s", "key": "k"}}')
        empty_pipeline.write_text("{}")
        pipeline_context["dbutils"].secrets.get.return_value = "pw"
        mgr = SecretsManager(schema, [str(secrets_file)], [str(empty_pipeline)])

        result = mgr.substitute_secrets({"password": "${secret.db_password}"})
        assert str(result["password"]) == "pw"
