Setting up CI/CD
################

Automate deployment of **Framework Bundles** and **Pipeline Bundles** using the same Databricks Asset Bundle (DAB) CLI pattern in your CI/CD agent.

For deploy order and ownership, see :doc:`before-you-deploy`.
For local development deploy, see :doc:`framework/local-framework` and :doc:`pipeline-bundle/local`.
For framework versioning, path layout, and pinning — see :doc:`features/environments/versioning-framework`.

Platform-specific examples (GitHub Actions, etc.): `CI/CD for DABs <https://docs.databricks.com/en/dev-tools/bundles/ci-cd-bundles.html>`_.

Prerequisites
=============

Before you begin, verify:

.. task-list::

   - [ ] **Databricks credentials** — access token or service principal for the CI/CD agent
   - [ ] **Python and Git** on the agent
   - [ ] **Bundle repository** access (framework or pipeline)

Shared workflow
===============

Both bundle types follow the same agent setup. Run these steps in order:

1. **Install the Databricks CLI** — skip if the agent image already includes it:

   .. code-block:: console
      :class: lf-command-block

      curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
      databricks --version

2. **Configure authentication** — PAT:

   .. code-block:: console
      :class: lf-command-block

      export DATABRICKS_HOST="https://<workspace-url>"
      export DATABRICKS_TOKEN="<pat-token>"

   Or OAuth service principal:

   .. code-block:: console
      :class: lf-command-block

      export DATABRICKS_CLIENT_ID="<client-id>"
      export DATABRICKS_CLIENT_SECRET="<client-secret>"

3. **Prepare the repository** — clone the bundle repo (framework or pipeline). For the framework repo, install validation dependencies:

   .. code-block:: console
      :class: lf-command-block

      pip install -r requirements.txt

4. **Validate the bundle**:

   .. code-block:: console
      :class: lf-command-block

      databricks bundle validate

5. **Deploy the bundle**:

   .. code-block:: console
      :class: lf-command-block

      databricks bundle deploy -t $ENVIRONMENT

   Pass bundle-specific variables with ``--var`` or ``BUNDLE_VAR_*`` environment variables as needed. Framework and pipeline jobs differ after this step — see below.

Framework releases in CI/CD
===========================

.. important::

   Framework versioning, ``framework_source_path``, and upgrade practices are documented in
   :doc:`features/environments/versioning-framework`. Read that page before configuring the Framework Bundle
   or setting version pins on Pipeline Bundles.

* **Repository:** Fork the upstream ``lakeflow_framework`` OSS repo into your organization; CI/CD deploys from your fork
* **Release cadence:** **Manually select** which upstream version to promote — review releases and deploy only after your platform team approves (avoid auto-deploy on every upstream tag or merge to main)
* **Versioned deploy:** Each release deploys to **both** ``current`` and the release version number (for example ``1.2.3``):

  * ``current`` — always points at the latest promoted release
  * ``<version>`` — a fixed copy in workspace files; keeps deploy history and enables pinning

.. code-block:: console
   :class: lf-command-block

   # Promote latest to current
   databricks bundle deploy --var="version=current" -t $ENVIRONMENT

   # Deploy the same release under its version number
   databricks bundle deploy --var="version=1.2.3" -t $ENVIRONMENT

.. note::

   Run both deploys in the **framework release** pipeline only — not on every pipeline-bundle job.

Example script (framework release)
----------------------------------

Illustrative bash script for a framework release job:

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

Pipeline bundles in CI/CD
=======================

* **Repository:** Team pipeline bundle
* **Trigger:** Merge or approval to promote across environments
* **Assumes:** Framework already deployed for the target environment (``current`` and any pinned version paths)
* **Variables:** Set ``framework_source_path`` per target (``current`` or a pinned version) — often from CI variables; see :doc:`features/environments/versioning-framework`

Pinning strategies
------------------

Each Pipeline Bundle chooses which framework path to use via ``framework_source_path`` (or ``BUNDLE_VAR_framework_source_path`` in CI/CD). Path patterns and examples: :doc:`features/environments/versioning-framework`.

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

Many teams default pipeline bundles to ``current`` in dev and production, pin specific pipelines during phased framework rollouts, and switch to a prior version path only when something breaks. Details: :doc:`features/environments/versioning-framework`.
