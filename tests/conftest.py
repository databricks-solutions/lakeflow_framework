"""
Shared pytest fixtures for Lakeflow Framework unit tests.

Agents: bootstrap pipeline singletons via ``pipeline_context`` — do not call
``initialize_core`` inline in individual test modules.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from helpers import make_tree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK_SRC = PROJECT_ROOT / "src"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

_PIPELINE_CONFIG_ATTRS = (
    "_spark",
    "_dbutils",
    "_logger",
    "_substitution_manager",
    "_pipeline_details",
    "_mandatory_table_properties",
    "_operational_metadata_schema",
    "_table_migration_state_volume_path",
)


def _snapshot_pipeline_config() -> dict[str, Any]:
    import pipeline_config as pc

    return {attr: getattr(pc, attr, None) for attr in _PIPELINE_CONFIG_ATTRS}


def _restore_pipeline_config(snapshot: dict[str, Any]) -> None:
    import pipeline_config as pc

    for attr, value in snapshot.items():
        setattr(pc, attr, value)


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def framework_src_path() -> Path:
    """Live framework ``src/`` tree (schemas, config)."""
    return FRAMEWORK_SRC


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def pipeline_context(tmp_path: Path):
    """
    Bootstrap ``pipeline_config`` singletons with mocks; restore after test.
    """
    from pipeline_config import (
        initialize_core,
        initialize_mandatory_table_properties,
        initialize_pipeline_details,
        initialize_substitution_manager,
    )
    from pipeline_details import PipelineDetails
    from substitution_manager import SubstitutionManager

    snapshot = _snapshot_pipeline_config()

    logger = logging.getLogger("lakeflow.test")
    logger.setLevel(logging.DEBUG)
    spark = MagicMock(name="SparkSession")
    dbutils = MagicMock(name="DBUtils")
    dbutils.secrets.get = MagicMock(return_value="secret-value")

    initialize_core(spark=spark, dbutils=dbutils, logger=logger)
    initialize_mandatory_table_properties({})
    initialize_pipeline_details(
        PipelineDetails(
            pipeline_id="test-pipeline",
            pipeline_catalog="test_catalog",
            pipeline_schema="test_schema",
            pipeline_layer="bronze",
            start_utc_timestamp="2020-01-01T00:00:00Z",
            workspace_env="dev",
            logical_env="dev",
        )
    )

    fw_path = tmp_path / "fw_substitutions.json"
    pl_path = tmp_path / "pl_substitutions.json"
    fw_path.write_text("{}")
    pl_path.write_text("{}")
    initialize_substitution_manager(
        SubstitutionManager([str(fw_path)], [str(pl_path)])
    )

    yield {
        "spark": spark,
        "dbutils": dbutils,
        "logger": logger,
        "framework_substitutions_path": fw_path,
        "pipeline_substitutions_path": pl_path,
    }

    _restore_pipeline_config(snapshot)


@pytest.fixture
def minimal_framework_tree(tmp_path: Path, framework_src_path: Path) -> Path:
    """
    Minimal framework bundle under *tmp_path* with schemas and default config.
    """
    import shutil

    fw = tmp_path / "framework"
    fw.mkdir()
    shutil.copytree(framework_src_path / "schemas", fw / "schemas")
    shutil.copytree(framework_src_path / "config" / "default", fw / "config" / "default")
    (fw / "VERSION").write_text("0.4.0-test\n")
    return fw


@pytest.fixture
def minimal_bundle_tree(tmp_path: Path) -> Path:
    """Minimal pipeline bundle with dataflows root and empty substitutions."""
    bundle = tmp_path / "bundle"
    make_tree(bundle, {
        "dataflows/.keep": "",
        "pipeline_configs/.keep": "",
        "_substitutions.json": '{"tokens": {}}',
    })
    return bundle


@pytest.fixture
def substitution_manager(tmp_path: Path, pipeline_context):
    """SubstitutionManager with framework + pipeline token files."""
    from pipeline_config import initialize_substitution_manager
    from substitution_manager import SubstitutionManager

    fw = tmp_path / "framework_substitutions.json"
    pl = tmp_path / "pipeline_substitutions.json"
    fw.write_text(
        (FIXTURES_DIR / "specs" / "framework_substitutions.json").read_text()
    )
    pl.write_text(
        (FIXTURES_DIR / "specs" / "pipeline_substitutions.json").read_text()
    )
    mgr = SubstitutionManager([str(fw)], [str(pl)])
    initialize_substitution_manager(mgr)
    return mgr


@pytest.fixture
def secrets_manager(tmp_path: Path, pipeline_context, framework_src_path):
    """SecretsManager with empty validated secrets config."""
    from secrets_manager import SecretsManager

    schema = str(framework_src_path / "schemas" / "secrets.json")
    fw = tmp_path / "framework_secrets.json"
    pl = tmp_path / "pipeline_secrets.json"
    fw.write_text("{}")
    pl.write_text("{}")
    return SecretsManager(schema, [str(fw)], [str(pl)])


@pytest.fixture
def template_bundle_tree(tmp_path: Path, fixtures_dir: Path) -> Path:
    """Bundle tree with minimal template for TemplateProcessor tests."""
    bundle = tmp_path / "bundle"
    template_src = fixtures_dir / "bundles" / "templates" / "minimal_template.json"
    make_tree(bundle, {
        "templates/minimal_template.json": template_src.read_text(),
        "dataflows/.keep": "",
    })
    return bundle


@pytest.fixture
def dataflow_bundle_tree(tmp_path: Path, fixtures_dir: Path) -> Path:
    """Bundle tree with one valid standard dataflow spec for builder integration tests."""
    import json

    bundle = tmp_path / "bundle"
    main_spec = json.loads(
        (fixtures_dir / "specs" / "expanded_main_minimal.json").read_text()
    )
    make_tree(bundle, {
        "dataflows/test_group/dataflowspec/minimal_flow_main.json": json.dumps(main_spec),
        "_substitutions.json": '{"tokens": {}}',
    })
    return bundle
