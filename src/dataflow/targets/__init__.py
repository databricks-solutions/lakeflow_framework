"""
Target auto-discovery and public exports.

Every ``.py`` file in this package (except ``__init__.py``) is imported
automatically at package load time.  Any class that inherits from
:class:`~dataflow.target.Target` and declares a ``target_type`` class
variable is registered in :attr:`~dataflow.target.TargetMeta.target_registry`
by the metaclass — no manual changes to this file are required when adding a
new target.

The explicit re-exports below make concrete classes available as
``from dataflow.targets import StreamingTableDelta`` for downstream code.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from dataflow.target import TargetMeta  # noqa: F401 — ensure Target is importable

# ------------------------------------------------------------------
# Auto-import every target module in this package.
# The act of importing causes TargetMeta to register each concrete
# Target subclass that declares a `target_type`.
# ------------------------------------------------------------------
_pkg = __name__
for _f in sorted(Path(__file__).parent.glob("*.py")):
    if _f.stem != "__init__":
        importlib.import_module(f".{_f.stem}", _pkg)

# ------------------------------------------------------------------
# Re-export concrete classes for named imports and backward compat.
# ------------------------------------------------------------------
from .delta_streaming_table import StreamingTableDelta       # noqa: E402
from .delta_materialized_view import MaterializedViewDelta   # noqa: E402
from .sink_delta import DeltaSink                            # noqa: E402
from .sink_kafka import KafkaSink                            # noqa: E402
from .sink_python_foreach_batch import PythonForEachBatchSink  # noqa: E402
from .sink_sql_foreach_batch import SqlForEachBatchSink      # noqa: E402
from .sink_custom_python import CustomPythonSink             # noqa: E402
from .staging_table import StagingTable                      # noqa: E402

__all__ = [
    "StreamingTableDelta",
    "MaterializedViewDelta",
    "DeltaSink",
    "KafkaSink",
    "PythonForEachBatchSink",
    "SqlForEachBatchSink",
    "CustomPythonSink",
    "StagingTable",
]
