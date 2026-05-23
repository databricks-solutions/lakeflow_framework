"""
Smoke tests for the ``lakeflow_framework`` package.

Verifies:
- ``import lakeflow_framework`` resolves correctly (package is on sys.path via src/).
- ``lakeflow_framework.__version__`` is a non-empty string.
- Core public API symbols are importable from the canonical path.
- Compat shims at ``src/*.py`` continue to re-export the same symbols.
"""
from __future__ import annotations

import sys


def test_import_package():
    import lakeflow_framework  # noqa: F401 — just ensure no ImportError


def test_version_is_set():
    import lakeflow_framework
    assert isinstance(lakeflow_framework.__version__, str)
    assert lakeflow_framework.__version__ != ""
    assert lakeflow_framework.__version__ != "unknown"


def test_core_api_importable():
    from lakeflow_framework import DLTPipelineBuilder
    from lakeflow_framework import DataflowSpecBuilder
    from lakeflow_framework import DataFlow
    from lakeflow_framework import DataflowSpec
    from lakeflow_framework import SecretsManager
    from lakeflow_framework import SubstitutionManager
    from lakeflow_framework.constants import FrameworkPaths, PipelineBundlePaths


def test_contrib_importable():
    import lakeflow_framework.contrib  # noqa: F401


def test_compat_shim_constants():
    """src/constants.py shim must re-export FrameworkPaths unchanged."""
    from lakeflow_framework.constants import FrameworkPaths as canonical
    from constants import FrameworkPaths as shim  # type: ignore[import]
    assert canonical is shim


def test_compat_shim_pipeline_config():
    """src/pipeline_config.py shim must export get_spark."""
    import pipeline_config  # type: ignore[import]
    assert hasattr(pipeline_config, "get_spark")


def test_compat_shim_dlt_pipeline_builder():
    """src/dlt_pipeline_builder.py shim must export DLTPipelineBuilder."""
    from dlt_pipeline_builder import DLTPipelineBuilder as shim  # type: ignore[import]
    from lakeflow_framework.dlt_pipeline_builder import DLTPipelineBuilder as canonical
    assert shim is canonical
