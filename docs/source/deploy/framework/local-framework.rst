Deploy framework from local machine
###################################

Deploy the **Lakeflow Framework** (Framework Bundle) to your Databricks workspace from your local machine using the Declarative Automation Bundle (DAB) CLI workflow.

For deployment modes (flat DAB deploy, wheel, wheel + overlay), see :doc:`/deploy/framework/options`.
For deploy order and ownership models, see :doc:`/deploy/before-you-deploy`.
For automated pipelines, see :doc:`/deploy/ci-cd`.

Prerequisites
=============

Before you begin, verify:

.. task-list::

   - [ ] **Databricks workspace** access with permission to deploy bundles
   - [ ] **Databricks CLI** installed — required for local Asset Bundle deployment (`CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_)
   - [ ] **CLI authentication** — run ``databricks auth login`` for your workspace, or use a configured CLI profile
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

From the **framework repository root** (clone ``lakeflow_framework``):

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

To deploy a specific framework version:

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t dev --var="version=1.2.3"

See :doc:`/deploy/ci-cd` and :doc:`/features/environments/versioning-framework` for version pinning in higher environments.

Step 5 — Verify the deployment
==============================

When deployment succeeds, framework source is present in your Databricks workspace under the ``.bundle`` directory for the deploying user (see ``workspace.root_path`` in ``databricks.yml``), typically under ``.bundle/<project>/<target>/<version>/files/src``.

Open the workspace UI and confirm bundle files are present, or inspect the path reported by the CLI deploy output.

Example — clone and deploy
==========================

.. code-block:: console
   :class: lf-command-block

   git clone https://github.com/databricks-solutions/lakeflow_framework.git
   cd lakeflow_framework
   databricks bundle validate
   databricks bundle deploy -t dev

See also
--------

- :doc:`/deploy/framework/options` — flat DAB deploy vs wheel install
- :doc:`/deploy/framework/wheel` — install ``lakeflow-framework`` as a Python wheel
- :doc:`/deploy/pipeline-bundle/local` — deploy a pipeline bundle after the framework is in place
