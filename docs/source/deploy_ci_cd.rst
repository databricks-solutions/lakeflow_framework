Setting up CI/CD
################

Automate deployment of **Framework Bundles** and **Pipeline Bundles** using the same Databricks Asset Bundle (DAB) CLI pattern in your CI/CD agent.

For deploy order and ownership, see :doc:`deploy_before_you_deploy`.
For local development deploy, see :doc:`deploy_local_framework` and :doc:`deploy_local_pipeline_bundle`.
For framework versioning, path layout, and pinning — see :doc:`feature_versioning_framework`.

Platform-specific examples (GitHub Actions, etc.): `CI/CD for DABs <https://docs.databricks.com/en/dev-tools/bundles/ci-cd-bundles.html>`_.

Prerequisites
=============

* Databricks access token or service principal for the CI/CD agent
* Python and Git on the agent
* Access to the bundle repository (framework or pipeline)

Shared CI/CD steps
==================

Step 1 — Install the Databricks CLI
===================================

If the agent image does not include the CLI:

.. code-block:: console
   :class: lf-command-block

   curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
   databricks --version

Step 2 — Configure authentication
=================================

.. code-block:: console
   :class: lf-command-block

   export DATABRICKS_HOST="https://<workspace-url>"
   export DATABRICKS_TOKEN="<pat-token>"

Or use OAuth service principal:

.. code-block:: console
   :class: lf-command-block

   export DATABRICKS_CLIENT_ID="<client-id>"
   export DATABRICKS_CLIENT_SECRET="<client-secret>"

Step 3 — Clone the bundle repository
====================================

Clone the repo that contains the bundle you are deploying (framework or pipeline).

Step 4 — Install validation dependencies (if required)
======================================================

For the framework repository:

.. code-block:: console
   :class: lf-command-block

   pip install -r requirements.txt

Step 5 — Validate the bundle
============================

.. code-block:: console
   :class: lf-command-block

   databricks bundle validate

Step 6 — Deploy the bundle
==========================

.. code-block:: console
   :class: lf-command-block

   databricks bundle deploy -t $ENVIRONMENT

Pass bundle-specific variables with ``--var`` or ``BUNDLE_VAR_*`` environment variables as needed.

Framework versioning
====================

.. important::

   Framework versioning, ``framework_source_path``, and upgrade practices are documented in
   :doc:`feature_versioning_framework`. Read that page before configuring CI/CD for the Framework Bundle
   or setting version pins on Pipeline Bundles.

Versioned deployment (framework release pipeline)
-------------------------------------------------

When deploying the **Framework Bundle** in CI/CD, use a **versioned deployment strategy**: deploy each release to **both** ``current`` and the **release version number** (for example ``1.2.3``).

* ``current`` — always points at the latest promoted release
* ``<version>`` — a fixed copy of that release in workspace files; keeps deploy history and enables pinning

.. code-block:: console
   :class: lf-command-block

   # Promote latest to current
   databricks bundle deploy --var="version=current" -t $ENVIRONMENT

   # Deploy the same release under its version number (run in the framework release pipeline)
   databricks bundle deploy --var="version=1.2.3" -t $ENVIRONMENT

.. note::

   Run both deploys in the **framework release** pipeline only — not on every pipeline-bundle job. Pipeline CI/CD assumes the target environment already has the ``current`` and versioned paths it needs.

Pinning strategies (pipeline bundles)
-------------------------------------

Each Pipeline Bundle chooses which framework path to use via ``framework_source_path`` (or ``BUNDLE_VAR_framework_source_path`` in CI/CD). The path includes the version segment — ``.../current/...`` or ``.../1.2.3/...``. See :doc:`feature_versioning_framework` for the full path pattern and examples.

.. list-table::
   :widths: 22 38 40
   :header-rows: 1

   * - Pin to
     - When to use
     - Effect
   * - ``current``
     - Default for most pipelines; you want pipelines to pick up framework fixes and features when the platform promotes a new release
     - Pipelines use the latest promoted framework after each framework deploy to ``current``
   * - Specific version (for example ``1.2.3``)
     - Controlled upgrades, gradual rollout, or testing a new framework release with selected pipelines before org-wide promotion
     - Pipelines stay on that version until you change ``framework_source_path``
   * - Prior version (for example ``1.2.2``)
     - A framework update causes a regression; you need to restore service quickly while the platform investigates
     - Point affected pipeline bundles at the last known-good version path — no framework redeploy required if that version is still in workspace files

Which strategy you use is an organizational choice. Many teams default pipeline bundles to ``current`` in dev and production, pin specific pipelines during phased framework rollouts, and switch to a prior version path only when something breaks. Details and best practices: :doc:`feature_versioning_framework`.

Framework bundle in CI/CD
=========================

* **Repository:** Fork the upstream ``lakeflow_framework`` OSS repo into your organization; CI/CD deploys from your fork
* **Release cadence:** Best practice is to **manually select** which upstream version to promote — review releases as they become available and deploy only after your platform team approves (avoid auto-deploy on every upstream tag or merge to main)
* **Versioned deploy:** each release deploys to ``current`` and to the release version number (for example ``1.2.3``)
* **Consumers:** pipeline bundles reference ``framework_source_path`` for the env

Pipeline bundle in CI/CD
========================

* **Repository:** team pipeline bundle
* **Trigger:** merge / approval to promote across environments
* **Assumes:** framework already deployed for the target environment
* **Variables:** set ``framework_source_path`` per target (``current`` or a pinned version) — often from CI variables; see :doc:`feature_versioning_framework`

Example script (framework release)
==================================

Illustrative bash script for a **framework** release job that validates, deploys ``current``, and deploys the same release under its version number:

.. code-block:: bash
   :class: lf-command-block

   #!/bin/bash
   set -e

   ENVIRONMENT=${1:-dev}
   RELEASE_VERSION=${2:?Set release version, e.g. 1.2.3}

   if ! command -v databricks &> /dev/null; then
       curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
   fi

   pip install -r requirements.txt
   databricks bundle validate

   echo "Deploying current to $ENVIRONMENT..."
   databricks bundle deploy --var="version=current" -t "$ENVIRONMENT"

   echo "Deploying version $RELEASE_VERSION to $ENVIRONMENT..."
   databricks bundle deploy --var="version=$RELEASE_VERSION" -t "$ENVIRONMENT"

   echo "Deployment complete."
