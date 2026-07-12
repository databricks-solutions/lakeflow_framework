Import conventions
##################

Framework code, tests, and scripts in this repository use the
``lakeflow_framework`` Python package namespace.  Flat ``src/`` import paths
exist only as backward-compatibility shims for existing pipeline bundles.

Canonical imports
-----------------

Use absolute imports from the package:

.. code-block:: python
   :linenos:

   from lakeflow_framework.constants import FrameworkPaths
   from lakeflow_framework.bundle_loader import BundleLoader
   from lakeflow_framework.dataflow import Dataflow

Implementation lives under ``src/lakeflow_framework/``.  That tree holds the
core modules, ``dataflow/``, ``dataflow_spec_builder/``, bundled default config
(``config/default/``), JSON schemas (``schemas/``), and the ``contrib/``
subpackage.

Compat shims (do not use in new code)
--------------------------------------

The old flat-deploy layout placed modules directly under ``src/`` (for example
``from constants import FrameworkPaths``).  Since v0.20.0, matching
``src/*.py`` files are thin re-export shims:

.. code-block:: python
   :linenos:

   # src/constants.py — compat shim, remove at v1.0.0
   from lakeflow_framework.constants import FrameworkPaths  # noqa: F401

Shims cover the top-level modules that used to live as bare ``src/*.py`` files
(``constants``, ``bundle_loader``, ``logger``, and similar).  They do **not**
duplicate ``dataflow/`` or ``dataflow_spec_builder/`` — those subpackages exist
only under ``src/lakeflow_framework/``.

Existing customer pipeline notebooks and bundles may keep bare imports until
v1.0.0.  **Contributors must not add new bare imports** in framework source,
tests, or repository scripts.

Rules for contributors
----------------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Context
     - Import rule
   * - Code under ``src/lakeflow_framework/``
     - Always ``from lakeflow_framework.<module> import ...``.  No bare imports
       and no relative imports across package boundaries.
   * - Unit and integration tests (``tests/``)
     - Always ``lakeflow_framework.*``.  Tests exercise the installed package,
       not the shim layer.
   * - Repository scripts (``scripts/``)
     - Prefer ``lakeflow_framework.*`` where the script imports framework
       modules.
   * - Sample pipeline bundles (``samples/``)
     - May use either style during the shim deprecation window; prefer
       ``lakeflow_framework.*`` in new sample code.
   * - ``src/local/``
     - Customer-owned overlay — not part of the published package.  See
       ``src/local/README.md``.

Local development
-----------------

For IDE resolution and ``pytest``, install the package in editable mode (see
:doc:`contributor_dev_env`):

.. code-block:: console
   :class: lf-command-block

   pip install -e ".[contrib]"

This puts ``lakeflow_framework`` on ``sys.path`` from ``src/lakeflow_framework/``
via ``pyproject.toml``.  You do not need to add ``src/`` manually when running
tests locally after an editable install.

Deprecation timeline
--------------------

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Version
     - Change
   * - v0.20.0
     - ``lakeflow_framework`` package introduced; bare ``src/`` imports still
       work via shims.
   * - v1.0.0
     - Compat shims at ``src/*.py`` removed.

Further reading
---------------

- ``docs/decisions/0008-lakeflow-framework-package.md`` — package layout,
  wheel distribution, and shim policy (ADR-0008).
- ``docs/decisions/0009-strategy-b-workspace-files-first-resolver.md`` — how bundled
  config and schemas resolve against workspace files (ADR-0009).
- :doc:`deploy_wheel` — wheel install and shim guidance for deployers.
- :doc:`contributor_contrib` — import rules specific to ``contrib/`` modules.
