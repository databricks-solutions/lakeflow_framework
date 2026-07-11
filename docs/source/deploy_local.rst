Deploy from local machine
#########################

Deploy a **Framework Bundle** or **Pipeline Bundle** to your Databricks workspace from your local machine.
Both use the same Declarative Automation Bundle (DAB) CLI workflow; only the working directory, prerequisites, and variables differ.

For deploy order and ownership models, see :doc:`deploy_before_you_deploy`.
For automated pipelines, see :doc:`deploy_ci_cd`.

Prerequisites
=============

Before you begin, verify:

- [ ] **Databricks workspace** access with permission to deploy bundles and run Lakeflow Spark Declarative Pipelines
- [ ] **Databricks CLI** installed — required for local Asset Bundle deployment ([CLI documentation](https://docs.databricks.com/dev-tools/cli/index.html))
- [ ] **CLI authentication** — run `databricks auth login` for your workspace, or use a configured CLI profile
- [ ] **Unity Catalog** enabled in your workspace

Step 1 — Authenticate the Databricks CLI
========================================

Authenticate against the workspace you will deploy to:

.. code-block:: console
   :class: lf-command-block

   databricks auth login --host https://<your-workspace-url>

Or use an existing named profile. Pass the profile on later commands with ``-p <profile>``:

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev -p <profile>

Step 2 — Configure the workspace host (optional)
================================================

Ensure the correct Databricks workspace is selected. Either:

* Leave ``workspace.host`` unset in ``databricks.yml`` so the CLI uses the host from the selected profile, or
* Set the host explicitly under the target you will deploy to.

The Databricks CLI must be authenticated with credentials that can access this workspace.

Step 3 — Validate the bundle
============================

From the **bundle root directory** (framework repo root or your pipeline bundle folder):

.. code-block:: console
   :class: lf-command-block

   databricks bundle validate

This runs checks to ensure the bundle is correctly set up and ready for deployment.

Step 4 — Deploy the bundle
==========================

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev

.. note::

   By default the CLI deploys to the ``dev`` target in ``databricks.yml``.
   Use ``-t <target>`` to deploy elsewhere and ``-p <profile>`` to select a different CLI profile.

Step 5 — Verify the deployment
==============================

When deployment succeeds, bundle files are present in your Databricks workspace under the ``.bundle`` directory for the deploying user (see ``workspace.root_path`` in ``databricks.yml``).

Open the workspace UI and confirm bundle files are present, or inspect the path reported by the CLI deploy output.

For pipeline bundles, also verify that a Spark Declarative Pipeline was created with the name defined in your ``resources/`` YAML.

.. _deploy_local_framework_notes:

Framework bundle
================

Use these notes when deploying the **Lakeflow Framework** itself.

* Run from the **framework repository root** (clone ``lakeflow_framework``).
* Deploys framework source to workspace files under ``.bundle/<project>/<target>/<version>/files/src``.
* To deploy a specific version: ``databricks bundle deploy -t dev --var="version=1.2.3"`` — see :doc:`deploy_ci_cd` and :doc:`feature_versioning_framework`.
* Shorter path including samples: :doc:`quick_start`.

Example — clone and deploy:

.. code-block:: console
   :class: lf-command-block

   git clone https://github.com/databricks-solutions/lakeflow_framework.git
   cd lakeflow_framework
   databricks bundle validate
   databricks bundle deploy -t dev

.. _deploy_local_pipeline_notes:

Pipeline bundle
===============

Use these notes when deploying a **Pipeline Bundle** you authored.

* Run from **your pipeline bundle** directory (after :doc:`build_pipeline_bundle_steps`).
* The **Framework Bundle must already be deployed** in the target workspace — central/platform path or your own dev deploy.
* Set ``framework_source_path`` in ``databricks.yml`` (or pass ``--var``) to the framework version in workspace, for example:

  ``/Workspace/Users/<owner>/.bundle/lakeflow_framework/dev/current/files/src``

* Deploy with the framework path when needed:

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev --var="framework_source_path=/Workspace/Users/<owner>/.bundle/lakeflow_framework/dev/current/files/src"

When pinning to a specific framework version for rollback, see :doc:`feature_versioning_framework`.
