from __future__ import annotations

from typing import ClassVar

from pyspark import pipelines as sdp

import utility
from dataflow.field import Field
from dataflow.target import Target
from dataflow.targets.mixins.sink import SinkMixin


class PythonForEachBatchSink(Target, SinkMixin):
    """
    For-each-batch sink that delegates to a user-supplied Python function.

    The batch function is loaded from either a module reference or a file path
    and called as ``fn(df, batch_id, tokens)`` for each micro-batch.

    Spec fields (``targetDetails`` keys)
    ------------------------------------
    * ``name``   — sink name (required)
    * ``config`` — dict with the following keys:

      * ``module``       — ``'pkg.module.function'`` dotted reference
      * ``functionPath`` — path to a ``.py`` file containing
                           ``micro_batch_function(df, batch_id, tokens)``
      * ``tokens``       — optional substitution-token dict passed to the
                           batch function

    Set ``"targetFormat": "python_foreach_batch_sink"`` in the spec.

    .. note::
       Backward-compat: the old ``"targetFormat": "foreach_batch_sink"`` with
       ``"type": "python_function"`` is remapped transparently by
       :meth:`~dataflow.dataflow_spec.DataflowSpec.get_target_details`.
    """

    target_type: ClassVar[str] = "python_foreach_batch_sink"
    config: dict = Field(default={})

    def create_target(self) -> None:
        module_ref = self.config.get("module")
        function_path = self.config.get("functionPath")
        tokens = self.config.get("tokens", {})

        sm = self.substitution_manager
        if tokens and sm:
            tokens = sm.substitute_dict(tokens)

        if module_ref:
            self.logger.debug(
                f"Loading batch function from module: {module_ref}"
            )
            batch_fn = utility.load_python_function_from_module(module_ref)
        elif function_path:
            self.logger.debug(
                f"Loading batch function from path: {function_path}"
            )
            batch_fn = utility.load_python_function(
                function_path,
                "micro_batch_function",
                ["df", "batch_id", "tokens"],
            )
        else:
            raise ValueError(
                f"PythonForEachBatchSink '{self.target_name}': config must "
                "specify either 'module' or 'functionPath'."
            )

        self.logger.info(
            f"Creating Python ForEachBatch Sink: {self.target_name}"
        )

        @sdp.foreach_batch_sink(name=self.target_name)
        def batch_function(df, batch_id):
            batch_fn(df, batch_id, tokens)
