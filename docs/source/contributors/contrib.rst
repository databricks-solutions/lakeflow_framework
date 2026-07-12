Contributing to ``lakeflow_framework.contrib``
##################################################

The ``lakeflow_framework.contrib`` subpackage is the home for optional,
community-maintained integrations.  It is deliberately separate from the core
framework so that:

* The core ``pip install lakeflow-framework`` stays lightweight with no
  extra dependencies.
* Community integrations can evolve at their own pace without affecting core
  stability guarantees.
* Individual integrations can be gated behind their own extras (e.g.
  ``pip install "lakeflow-framework[contrib.myintegration]"``).

.. _contrib-deploy-context:

Deployment context: wheel vs. flat DAB deploy
----------------------------------------------

Contrib modules live inside the ``lakeflow_framework`` package tree and
therefore behave differently depending on how the framework is deployed.
Understanding both modes is important when writing or using a contrib module.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Mode
     - How the framework is available
     - How contrib modules are available
   * - **Wheel install**
     - ``pip install lakeflow-framework`` via PyPI, UC Volume, or Artifactory.
       The entire ``lakeflow_framework`` package — including ``contrib/`` — is
       installed into the cluster Python environment.
     - ``pip install "lakeflow-framework[contrib]"`` (or the specific
       sub-extra).  No further path setup needed.
   * - **Flat DAB deploy**
     - The framework repository is cloned and deployed via
       ``databricks bundle deploy``.  ``framework.sourcePath`` points to the
       ``src/`` directory on workspace files, and Databricks adds it to
       ``sys.path`` at pipeline start.
     - ``src/lakeflow_framework/contrib/`` is on ``sys.path`` automatically
       because ``src/`` is.  However, any *external* dependencies declared by
       the contrib module still need to be installed separately — they are not
       bundled with the flat deploy.  Install them as cluster libraries or
       via ``src/local/libraries/`` (see :doc:`/features/python/extensions`).
   * - **Wheel + local overlay**
     - Wheel installed, plus ``framework.sourcePath`` set for
       ``src/local/config/`` sparse overrides.
     - Same as wheel install — contrib is available from the wheel.

.. admonition:: Contrib vs. pipeline-bundle custom code
   :class: note

   ``contrib`` is for **reusable framework-level integrations** that benefit
   many teams (e.g. a connector, a utility class, an alternative logger
   backend).  Pipeline-specific Python — transforms, domain logic, helper
   functions used by a single pipeline — belongs in the pipeline bundle under
   ``src/local/python/`` or ``src/python/``, not in ``contrib``.

Support policy
--------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Property
     - Policy
   * - **Install gate**
     - ``pip install "lakeflow-framework[contrib]"`` (or the specific sub-extra
       for the integration).
   * - **Stability label**
     - All contrib modules carry the **experimental** label until explicitly
       graduated.  Breaking changes between minor releases are allowed for
       experimental modules.
   * - **Stability graduation**
     - A module graduates to *stable* via a PR that removes the experimental
       label and passes a core-team review.  Once stable, normal semver
       deprecation rules apply.
   * - **External dependencies**
     - Must be declared as optional extras in ``pyproject.toml``.  A plain
       ``pip install lakeflow-framework`` must not pull them in.  For flat
       DAB deploy, contributors must document how to install them separately
       (cluster libraries or ``src/local/libraries/``).
   * - **Review scope**
     - Maintainers review for safety and conformance with framework conventions.
       Feature completeness is the contributor's responsibility.

Adding a new contrib module
---------------------------

1. **Create the module directory**

   .. code-block:: text

      src/lakeflow_framework/contrib/<your_module>/
      ├── __init__.py
      └── README.rst     ← required: purpose, status, external deps

2. **Declare the extra in ``pyproject.toml``**

   Add a new entry under ``[project.optional-dependencies]``:

   .. code-block:: toml

      [project.optional-dependencies]
      contrib = []
      contrib.myintegration = ["some-third-party>=1.0"]
      all = ["lakeflow-framework[contrib]", "lakeflow-framework[contrib.myintegration]"]

3. **Write a ``README.rst``**

   The README must state:

   * Purpose of the integration.
   * Stability label (``experimental`` until graduated).
   * Required external dependencies and minimum versions.
   * **Install instructions for both deploy modes:**

     * Wheel: ``pip install "lakeflow-framework[contrib.myintegration]"``
     * Flat DAB deploy: how to install external deps as cluster libraries or
       via ``src/local/libraries/``.
   * Basic usage example.

4. **Add tests**

   Tests for contrib modules must be gated behind the relevant extra.  The
   easiest pattern is a ``pytest.importorskip`` at the top of the test module:

   .. code-block:: python
      :linenos:

      some_dep = pytest.importorskip("some_third_party")

   This ensures the test is skipped (not failed) when the extra is not
   installed.

5. **Open a pull request**

   Follow the standard PR process in :doc:`/contributors/dev-steps`.  In the PR
   description, note:

   * The extra name being added.
   * A brief rationale for why this belongs in ``contrib`` rather than the
     core.
   * Any known limitations or areas not yet covered.

Module conventions
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Convention
     - Details
   * - **``__init__.py``**
     - Import only what is needed.  Avoid heavy imports at module-load time
       — use lazy imports if the external dependency is optional even within
       the contrib module.
   * - **Naming**
     - Use ``snake_case`` for module directories.  Avoid names that conflict
       with top-level PyPI packages.
   * - **Logging**
     - Use the framework logger (``from lakeflow_framework.logger import
       get_logger``) rather than ``print`` or a bare ``logging.getLogger``.
   * - **No private framework internals**
     - Contrib modules must import only from the public ``lakeflow_framework``
       API (``lakeflow_framework.*``).  Importing from
       ``lakeflow_framework._private.*`` is not allowed and will break without
       notice.

See also
--------

- ``src/lakeflow_framework/contrib/README.rst`` in the repository — the
  in-source support policy document.
- :doc:`/contributors/dev-steps` — general contribution workflow.
- :doc:`/contributors/dev-env` — development environment setup.
