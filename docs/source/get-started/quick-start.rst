Quick Start
###########

Get the Lakeflow Framework (LFF) deployed and running sample pipelines in your Databricks workspace in about **15–20 minutes**.

Prerequisites
=============

Before you begin, verify:

.. task-list::

   - [ ] **Databricks workspace** access with permission to deploy bundles and run Lakeflow Spark Declarative Pipelines
   - [ ] **Databricks CLI** installed — required for local Asset Bundle deployment (`CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_)
   - [ ] **CLI authentication** — run ``databricks auth login`` for your workspace, or use a configured CLI profile
   - [ ] **Unity Catalog** enabled in your workspace
   - [ ] **UC catalog** already exists for sample deployment (default ``main``, or pass another with ``--catalog``) — the deploy scripts create schemas in that catalog, not the catalog itself
   - [ ] Familiarity with `Lakeflow Spark Declarative Pipelines <https://docs.databricks.com/aws/en/ldp/>`_ concepts (helpful, not required)
   - [ ] **IDE installed (optional)** — for example VS Code or Cursor, used for Data Flow Spec IntelliSense

.. tip::

   **New to Asset Bundles?** The framework ships as a Declarative Automation Bundle (DAB). Authenticate the CLI first, then optionally set the workspace host in ``databricks.yml`` (or leave it unset to use the host from your CLI profile). See :doc:`deploy/index` for the full deploy workflow.

Step 1 — Clone the repository
=============================

1. Open a terminal on your local machine
2. Clone the repository and enter the project directory:

.. code-block:: console
   :class: lf-command-block

   git clone https://github.com/databricks-solutions/lakeflow_framework.git
   cd lakeflow_framework

Step 2 — Authenticate the Databricks CLI
========================================

Authenticate against the workspace you will deploy to:

.. code-block:: console
   :class: lf-command-block

   databricks auth login --host https://<your-workspace-url>

Or use an existing named profile (for example after ``databricks auth login --profile <name>``):

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev -p <profile>

.. note::

   You can set ``targets.dev.workspace.host`` in ``databricks.yml``, or leave the host unset so the CLI uses the host from the selected profile. See :doc:`deploy/framework/local-framework` for details.

Step 3 — Deploy the framework
=============================

From the **repository root**:

1. Validate the framework bundle

.. code-block:: console
   :class: lf-command-block

   databricks bundle validate

2. Deploy to your workspace

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev

.. note::

   By default the CLI deploys to the ``dev`` target in ``databricks.yml``. Use ``-t <target>`` to deploy elsewhere and ``-p <profile>`` to select a different CLI profile.

**Full reference:** :doc:`deploy/index`

Step 4 — Deploy the samples
===========================

Samples require the framework deploy above. ``./deploy.sh`` deploys the full sample set (feature-samples and pattern-samples). For bundle descriptions and other scripts, see ``samples/README.md`` in the repository.

From the ``samples/`` directory:

.. code-block:: console
   :class: lf-command-block

   cd samples

.. warning::

   **Always set a logical environment when deploying.** Specify a unique logical environment suffix when executing the deploy script so your sample schemas and jobs do not overwrite another user's deployment in a shared workspace.

   Suggested naming: your initials (``_jd``), a story ID (``_123456``), a client or team name, or a project name.

Choose either interactive or command-line deploy.

Option A — Interactive
--------------------

Run with no flags and answer the prompts:

.. code-block:: console
   :class: lf-command-block

   ./deploy.sh

.. list-table::
   :header-rows: 1
   :widths: 25 45 30

   * - Prompt
     - Purpose
     - Default / notes
   * - Databricks username
     - Your workspace user (e.g. ``jane.doe@company.com``)
     - —
   * - Workspace host
     - Full workspace URL (e.g. ``https://company.cloud.databricks.com``)
     - —
   * - CLI profile
     - Named CLI profile
     - ``DEFAULT``
   * - Compute
     - ``0`` = classic/enhanced, ``1`` = serverless
     - ``1``
   * - UC catalog
     - Existing target catalog
     - ``main``
   * - Schema namespace
     - Prefix for sample schemas
     - ``lakeflow_samples``
   * - Logical environment
     - Isolation suffix (e.g. ``_jd``)
     - —

Schema namespaces created:

* **feature-samples:** ``{namespace}_feature{logical_env}``
* **pattern-samples:** ``{namespace}_staging{logical_env}``, ``{namespace}_bronze{logical_env}``, ``{namespace}_silver{logical_env}``, ``{namespace}_gold{logical_env}``

Option B — Command-line
-----------------------

Pass all required parameters in one command (no prompts):

.. code-block:: console
   :class: lf-command-block

   ./deploy.sh \
     -u <databricks_username> \
     -h <workspace_host> \
     [-p <profile>] \
     [-c <compute>] \
     [-l <logical_env>] \
     [--catalog <catalog>] \
     [--schema_namespace <schema_namespace>]

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Flag
     - Purpose
     - Default
   * - ``-u`` / ``--user``
     - Workspace user (required)
     - —
   * - ``-h`` / ``--host``
     - Workspace URL (required)
     - —
   * - ``-p`` / ``--profile``
     - CLI profile
     - ``DEFAULT``
   * - ``-c`` / ``--compute``
     - ``0`` = classic/enhanced, ``1`` = serverless
     - ``1``
   * - ``-l`` / ``--logical_env``
     - Isolation suffix
     - ``_test``
   * - ``--catalog``
     - Existing UC catalog
     - ``main``
   * - ``--schema_namespace``
     - Schema name prefix
     - ``lakeflow_samples``

Example:

.. code-block:: console
   :class: lf-command-block

   ./deploy.sh -u jane.doe@company.com -h https://company.cloud.databricks.com -l _jd -c 1

Step 5 — Run the feature samples
================================

1. In the Databricks workspace, open **Workflows** and locate the job:

   **``Lakeflow Framework - Feature Samples - Run (<logical_env>)``**

   Or run from the CLI (from the ``samples/feature-samples`` bundle directory after deploy):

   .. code-block:: console
      :class: lf-command-block

      databricks bundle run feature_samples_run_job -t dev

2. When the job completes, inspect tables in the **``{namespace}_feature{logical_env}``** schema (for example ``lakeflow_samples_feature_jd``).

This is the simplest entry point — every framework feature runs in a single schema.

Step 6 — Enable VS Code IntelliSense
====================================

Add the framework JSON schemas to your VS Code ``settings.json`` so Data Flow specs get auto-complete and validation.

1. Open **Command Palette** → **Preferences: Open User Settings (JSON)**
2. Register schemas for ``*_main.json``, ``*_flow.json``, and related spec files

**Full configuration and examples:** :doc:`features/authoring/auto-complete`

Step 7 — Understand the framework
=================================

Read :doc:`architecture/index` for architecture and operating models, then browse :doc:`features/index` for what you can configure.

What's next?
============

* **Build your first pipeline** — :doc:`build/index` (select a pattern from :doc:`build/patterns/index`, then follow the build steps)
* **Deploy via CI/CD** — :doc:`deploy/ci-cd`
* **Data Flow Spec reference** — :doc:`build/spec-reference/index`
