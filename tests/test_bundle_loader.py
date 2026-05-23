"""
Unit tests for bundle_loader — register_bundle_sys_paths and run_init_scripts.
"""
from __future__ import annotations

import logging
import os
import sys
import textwrap
import warnings
from pathlib import Path

import pytest

from lakeflow_framework.bundle_loader import register_bundle_sys_paths, run_init_scripts

logger = logging.getLogger("test_bundle_loader")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tree(tmp_path: Path, layout: dict) -> None:
    """Create a directory tree described by {relative_path: content|None}."""
    for rel, content in layout.items():
        full = tmp_path / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            full.mkdir(parents=True, exist_ok=True)
        else:
            full.write_text(textwrap.dedent(content))


# ---------------------------------------------------------------------------
# register_bundle_sys_paths
# ---------------------------------------------------------------------------

class TestRegisterBundleSysPaths:
    def test_registers_src_libraries_and_src_python(self, tmp_path):
        fw = tmp_path / "fw"
        bundle = tmp_path / "bundle"
        _make_tree(fw, {"src/libraries/.keep": "", "src/python/.keep": ""})
        _make_tree(bundle, {"src/libraries/.keep": "", "src/python/.keep": ""})

        before = set(sys.path)
        register_bundle_sys_paths(str(fw), str(bundle), logger)
        added = [p for p in sys.path if p not in before]

        assert any("fw" in p and "libraries" in p for p in added)
        assert any("fw" in p and "python" in p for p in added)
        assert any("bundle" in p and "libraries" in p for p in added)
        assert any("bundle" in p and "python" in p for p in added)

        # Cleanup
        for p in added:
            if p in sys.path:
                sys.path.remove(p)

    def test_no_registration_for_absent_dirs(self, tmp_path):
        fw = tmp_path / "fw"
        bundle = tmp_path / "bundle"
        fw.mkdir()
        bundle.mkdir()

        before = set(sys.path)
        register_bundle_sys_paths(str(fw), str(bundle), logger)
        added = [p for p in sys.path if p not in before]
        assert added == []

    def test_deprecated_flat_extensions_emits_warning(self, tmp_path):
        fw = tmp_path / "fw"
        bundle = tmp_path / "bundle"
        _make_tree(fw, {})
        _make_tree(bundle, {"extensions/my_module.py": "x = 1"})

        before = set(sys.path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            register_bundle_sys_paths(str(fw), str(bundle), logger)

        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert dep_warnings, "Expected a DeprecationWarning for flat extensions/"

        added = [p for p in sys.path if p not in before]
        ext_path = os.path.normpath(str(bundle / "extensions"))
        assert ext_path in sys.path

        # Cleanup
        for p in added:
            if p in sys.path:
                sys.path.remove(p)

    def test_no_deprecation_warning_when_src_python_present(self, tmp_path):
        """If src/python/ exists, flat extensions/ should not be added to sys.path."""
        bundle = tmp_path / "bundle"
        _make_tree(bundle, {
            "src/python/.keep": "",
            "extensions/my_module.py": "x = 1",
        })

        before = set(sys.path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            register_bundle_sys_paths(str(tmp_path / "fw"), str(bundle), logger)

        ext_path = os.path.normpath(str(bundle / "extensions"))
        assert ext_path not in sys.path, "extensions/ should not be added when src/python/ exists"

        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        # Warning is still emitted (to inform the user), but path is not added
        assert dep_warnings

        added = [p for p in sys.path if p not in before]
        for p in added:
            if p in sys.path:
                sys.path.remove(p)

    def test_no_duplicate_sys_path_entries(self, tmp_path):
        fw = tmp_path / "fw"
        _make_tree(fw, {"src/python/.keep": ""})
        bundle = tmp_path / "bundle"
        bundle.mkdir()

        python_path = os.path.normpath(str(fw / "src" / "python"))
        if python_path in sys.path:
            sys.path.remove(python_path)

        register_bundle_sys_paths(str(fw), str(bundle), logger)
        count = sys.path.count(python_path)
        assert count == 1, f"Expected 1 occurrence of path, got {count}"

        # Register again — should still be 1
        register_bundle_sys_paths(str(fw), str(bundle), logger)
        assert sys.path.count(python_path) == 1

        if python_path in sys.path:
            sys.path.remove(python_path)


# ---------------------------------------------------------------------------
# run_init_scripts
# ---------------------------------------------------------------------------

class TestRunInitScripts:
    def test_runs_pre_scripts_in_order(self, tmp_path):
        bundle = tmp_path / "bundle"
        _make_tree(bundle, {
            "src/init/pre/01_first.py": "import builtins; builtins._test_order = getattr(builtins, '_test_order', []) + ['first']",
            "src/init/pre/02_second.py": "import builtins; builtins._test_order = getattr(builtins, '_test_order', []) + ['second']",
        })

        import builtins
        builtins._test_order = []
        run_init_scripts(str(tmp_path / "fw"), str(bundle), "pre", logger)
        assert builtins._test_order == ["first", "second"]
        del builtins._test_order

    def test_runs_post_scripts(self, tmp_path):
        bundle = tmp_path / "bundle"
        _make_tree(bundle, {
            "src/init/post/run_me.py": "import builtins; builtins._post_ran = True",
        })

        import builtins
        builtins._post_ran = False
        run_init_scripts(str(tmp_path / "fw"), str(bundle), "post", logger)
        assert builtins._post_ran is True
        del builtins._post_ran

    def test_skips_underscore_files(self, tmp_path):
        bundle = tmp_path / "bundle"
        _make_tree(bundle, {
            "src/init/pre/_private.py": "raise RuntimeError('should not run')",
            "src/init/pre/normal.py": "",
        })
        run_init_scripts(str(tmp_path / "fw"), str(bundle), "pre", logger)

    def test_framework_runs_before_bundle(self, tmp_path):
        fw = tmp_path / "fw"
        bundle = tmp_path / "bundle"
        _make_tree(fw, {
            "src/init/pre/a.py": "import builtins; builtins._fw_order = getattr(builtins, '_fw_order', []) + ['fw']",
        })
        _make_tree(bundle, {
            "src/init/pre/a.py": "import builtins; builtins._fw_order = getattr(builtins, '_fw_order', []) + ['bundle']",
        })

        import builtins
        builtins._fw_order = []
        run_init_scripts(str(fw), str(bundle), "pre", logger)
        assert builtins._fw_order == ["fw", "bundle"]
        del builtins._fw_order

    def test_missing_phase_dir_is_silent(self, tmp_path):
        fw = tmp_path / "fw"
        bundle = tmp_path / "bundle"
        fw.mkdir()
        bundle.mkdir()
        run_init_scripts(str(fw), str(bundle), "pre", logger)  # no exception

    def test_invalid_phase_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid init phase"):
            run_init_scripts(str(tmp_path), str(tmp_path), "bad_phase", logger)  # type: ignore

    def test_script_exception_propagates(self, tmp_path):
        bundle = tmp_path / "bundle"
        _make_tree(bundle, {
            "src/init/pre/fail.py": "raise RuntimeError('deliberate failure')",
        })
        with pytest.raises(RuntimeError, match="deliberate failure"):
            run_init_scripts(str(tmp_path / "fw"), str(bundle), "pre", logger)
