Before you deploy
#################

Read this page first. It explains **deploy order**, **who deploys what** across environments, and **where bundle files land** in the workspace — before you use the local or CI/CD guides.

Deploy order
============

Pipeline bundles depend on a deployed framework at a known ``framework_source_path``. Deploy the **Framework Bundle** first, then **Pipeline Bundle(s)**.

**Framework Bundle** → **Pipeline Bundle(s)** → pipelines run in the workspace.

.. mermaid::

   flowchart LR
     Fw["1. Framework Bundle"] --> Pipe["2. Pipeline Bundle(s)"]
     Pipe --> Run["SDP pipelines run"]

Both bundle types use the same Databricks CLI workflow — authenticate, validate, deploy — but differ in bundle root, workspace path, and variables:

* **Framework Bundle** — framework source under workspace files (for example ``.bundle/.../files/src``)
* **Pipeline Bundle** — your data flows and Spark Declarative Pipeline definitions; requires the framework already deployed at ``framework_source_path``

When building pipeline bundles, confirm the framework is available first — see :doc:`build_pipeline_bundle_steps`.

Who deploys what
================

.. list-table::
   :widths: 22 28 25 25
   :header-rows: 1

   * - Bundle
     - Typical owner
     - Dev
     - Test / staging / prod
   * - **Framework**
     - Platform team (central) or federated platform per domain
     - CI/CD as an owning service principal (SP) — same pattern as higher tiers
     - CI/CD as an owning SP; versioned promote to a shared or secured workspace path
   * - **Pipeline**
     - Data / domain teams
     - Developer deploys from laptop during inner loop
     - CI/CD as an owning SP after merge / approval

Central vs federated framework deployment is an organizational choice. The docs describe both without prescribing one model.

**Framework Bundle** — in most organizations the framework is deployed **the same way in every environment** (dev through prod): platform CI/CD authenticates as an **owning service principal**, not as an individual developer. Solo dev or POC work may still deploy the framework to a developer's workspace files for experimentation; that is the exception, not the standard.

**Pipeline Bundle** — deployment identity usually **depends on the environment**:

* **Dev** — developers deploy locally from their machine while authoring and testing data flows
* **All other environments** — CI/CD deploys as an **owning SP**, consistent with the framework pattern above

Service principals and workspace paths
======================================

When deploying as an SP (framework in all environments; pipeline bundles outside dev), the SP is the **owner** of the bundle in that workspace. CI/CD jobs authenticate as that SP (or a deployment SP permitted to act on its behalf) so ownership, ACLs, and audit trails stay consistent across promotions.

Bundle files can land in one of two workspace locations:

* **SP workspace files** — default DAB layout under the SP's user folder, for example ``/Workspace/Users/<sp-name>/.bundle/.../files/src``
* **Designated secured folder** — a shared, ACL-controlled path under workspace files (for example ``/Workspace/Shared/platform/lakeflow_framework/...``) that platform teams manage and pipeline bundles reference via ``framework_source_path``

Which path you use is an org choice. The framework is commonly deployed to a secured shared folder or the platform SP's ``.bundle`` path in every environment; pipeline bundles in dev typically use the developer's workspace files, then switch to an SP-owned path when promoted.

Next steps
==========

* :doc:`deploy_local_framework` — deploy the framework from your laptop (dev inner loop)
* :doc:`deploy_local_pipeline_bundle` — deploy a pipeline bundle from your laptop
* :doc:`deploy_ci_cd` — automate deploy with CI/CD, including framework versioning
