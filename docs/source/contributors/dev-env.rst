Set up your environment
#######################

Prepare a local development environment for contributing to the Lakeflow Framework — clone the repo, install dependencies, and configure your editor.

For the full contribution path after setup, see :doc:`/contributors/dev-steps`.
For import rules, see :doc:`/contributors/imports`.
For documentation lockfiles and ``make html``, see :doc:`/contributors/dev-docs`.

Prerequisites
=============

Before you begin, verify:

.. task-list::

   - [ ] **Git** installed
   - [ ] **Python 3.10+** installed (see ``requires-python`` in ``pyproject.toml``)
   - [ ] **pip** available in your shell
   - [ ] **IDE (optional)** — VS Code or Cursor recommended for Data Flow Spec IntelliSense and yapf formatting

Step 1 — Clone the repository
===============================

Open a terminal and clone the framework repository:

.. code-block:: console
   :class: lf-command-block

   git clone https://github.com/databricks-solutions/lakeflow_framework.git
   cd lakeflow_framework

Step 2 — Create a virtual environment (recommended)
===================================================

Use a virtual environment so project dependencies stay isolated from your system Python. See `Python Virtual Environments <https://docs.python.org/3/tutorial/venv.html>`_ for details.

.. code-block:: console
   :class: lf-command-block

   python -m venv .venv
   source .venv/bin/activate

On Windows, activate with ``.venv\Scripts\activate``.

Step 3 — Install dev dependencies
=================================

The dev dependencies are pinned and hash-verified in ``requirements-dev.lock`` (generated from ``requirements-dev.txt``). Installing from the lockfile guarantees a reproducible environment that matches CI.

From the **repository root**:

.. code-block:: console
   :class: lf-command-block

   pip install --require-hashes --no-deps -r requirements-dev.lock

``requirements-dev.lock`` includes everything in ``requirements-docs.lock``, so you do not need a separate install step for building documentation.

.. note::

   ``--require-hashes`` makes ``pip`` verify each package against the lockfile.
   ``--no-deps`` is safe here because the lockfile already contains the full resolved dependency set.

Step 4 — Optional: editable install for IDE and pytest
======================================================

For a lighter setup that resolves imports without locking all transitive hashes (useful for IDE auto-complete and local ``pytest`` runs):

.. code-block:: console
   :class: lf-command-block

   pip install -e ".[contrib]"

This installs the framework in editable mode from ``pyproject.toml``, including the ``[contrib]`` extra. Use ``pip install -e ".[all]"`` to pull in future contrib sub-extras as they land.

Build a distribution wheel at any time with:

.. code-block:: console
   :class: lf-command-block

   python -m build

Step 5 — Set up VS Code extensions
====================================

Open the Lakeflow Framework workspace in VS Code (or Cursor). On first open, the editor prompts you to install **recommended workspace extensions**.

If you missed the prompt:

* Run **Extensions: Show Recommended Extensions**, or
* Open the Extensions view and select **Workspace Recommendations**

Install the recommended extensions — including **yapf** for Python formatting used in :doc:`/contributors/dev-steps`.

Step 6 — Verify the setup
=========================

From the repository root, confirm unit tests run:

.. code-block:: console
   :class: lf-command-block

   pytest tests/ -m "not integration and not spark"

See ``tests/README.md`` for layout, markers, and conventions.

When you change dependencies
============================

If you add, remove, or bump a dependency in any ``requirements*.txt`` file, regenerate all lockfiles from the repo root:

.. code-block:: console
   :class: lf-command-block

   ./scripts/generate_lockfiles.sh

Commit the regenerated ``.lock`` files with your dependency change. See :doc:`/contributors/dev-docs` for documentation lockfile details.

.. note::

   To deploy the framework to a Databricks workspace for integration testing, follow :doc:`/deploy/framework/local-framework` or :doc:`/get-started/quick-start`.

See also
--------

- :doc:`/index` — Contributors hub
- :doc:`/contributors/dev-steps` — contribution workflow
- :doc:`/contributors/imports` — ``lakeflow_framework.*`` import conventions
- :doc:`/contributors/dev-docs` — write and build documentation
