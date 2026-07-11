``lakeflow_framework.contrib`` — Community Extensions
=====================================================

.. warning::

   This sub-package is **experimental**.  Modules here are community-maintained,
   may change without a deprecation window, and are not covered by the core
   stability guarantee.

Support policy
--------------

* ``contrib`` modules are gated behind the ``[contrib]`` extra:

  .. code-block:: bash

      pip install "lakeflow-framework[contrib]"

* Stability label: **experimental** — breaking changes are allowed between
  minor releases while a module carries this label.
* Each module documents its own external dependencies; they must be listed as
  optional extras in ``pyproject.toml`` under the relevant sub-extra (e.g.
  ``[contrib.myintegration]``) so that a plain ``pip install lakeflow-framework``
  does not pull them in.
* Community contributions follow the same PR process as core; the maintainers
  review for safety and conformance, not for feature completeness.

Adding a new contrib module
---------------------------

1. Create ``src/lakeflow_framework/contrib/<your_module>/``.
2. Add any required third-party dependencies as a new extra in ``pyproject.toml``.
3. Include a README (``README.rst`` or ``README.md``) describing the integration,
   its status, and its external requirements.
4. Add CI tests gated behind the ``[contrib]`` install.
