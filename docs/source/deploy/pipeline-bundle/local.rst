Deploy pipeline bundle from local machine
#########################################

Deploy a **Pipeline Bundle** you authored to your Databricks workspace from your local machine using the Declarative Automation Bundle (DAB) CLI workflow.

The **Framework Bundle must already be deployed** in the target workspace — central/platform path or your own dev deploy. See :doc:`/deploy/before-you-deploy` for deploy order.

For deploy order and ownership models, see :doc:`/deploy/before-you-deploy`.
For automated pipelines, see :doc:`/deploy/ci-cd`.

Prerequisites
=============

Before you begin, verify:

.. task-list::

   - [ ] **Databricks workspace** access with permission to deploy bundles and run Lakeflow Spark Declarative Pipelines
   - [ ] **Databricks CLI** installed — required for local Asset Bundle deployment (`CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_)
   - [ ] **CLI authentication** — run ``databricks auth login`` for your workspace, or use a configured CLI profile
   - [ ] **Unity Catalog** enabled in your workspace
   - [ ] **Framework deployed** at a known ``framework_source_path`` in this workspace

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

Step 3 — Set the framework source path
======================================

Point your pipeline bundle at the deployed framework version in workspace files. Set ``framework_source_path`` in ``databricks.yml`` (or pass ``--var``), for example:

``/Workspace/Users/<owner>/.bundle/lakeflow_framework/dev/current/files/src``

If you deployed the framework yourself for local dev, the default path is under your user ``.bundle/.../files/src``. See :doc:`/deploy/framework/local-framework`.

Step 4 — Validate the bundle
============================

From **your pipeline bundle** directory (after :doc:`/build/bundle-steps`):

.. code-block:: console
   :class: lf-command-block

   databricks bundle validate

This runs checks to ensure the bundle is correctly set up and ready for deployment.

Step 5 — Deploy the bundle
==========================

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev

When the framework path is not already set in ``databricks.yml``, pass it at deploy time:

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev --var="framework_source_path=/Workspace/Users/<owner>/.bundle/lakeflow_framework/dev/current/files/src"

.. note::

   By default the CLI deploys to the ``dev`` target in ``databricks.yml``.
   Use ``-t <target>`` to deploy elsewhere and ``-p <profile>`` to select a different CLI profile.

When pinning to a specific framework version for rollback, see :doc:`/features/environments/versioning-framework`.

Step 6 — Verify the deployment
==============================

When deployment succeeds, bundle files are present in your Databricks workspace under the ``.bundle`` directory for the deploying user (see ``workspace.root_path`` in ``databricks.yml``).

Open the workspace UI and confirm bundle files are present, or inspect the path reported by the CLI deploy output.

Verify that a Spark Declarative Pipeline was created with the name defined in your ``resources/`` YAML.

See also
--------

- :doc:`/build/bundle-steps` — build a pipeline bundle before deploy
- :doc:`/deploy/framework/local-framework` — deploy the framework first
- :doc:`/features/environments/versioning-framework` — version pinning and rollback
