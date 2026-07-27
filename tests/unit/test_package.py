"""
Smoke tests for the ``lakeflow_framework`` package.

Verifies canonical imports only — the test suite does not exercise compat shims.
"""
from __future__ import annotations


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
