Building a Pipeline Bundle
##########################

Create a Pipeline Bundle, configure it, author data flows, and define Spark Declarative Pipelines.

Prerequisites
=============

Before you begin, verify:

.. task-list::

   - [ ] **Databricks workspace** access with permission to deploy bundles and run Lakeflow Spark Declarative Pipelines
   - [ ] **Databricks CLI** installed — required for local Asset Bundle deployment (`CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_)
   - [ ] **CLI authentication** — run ``databricks auth login`` for your workspace, or use a configured CLI profile
   - [ ] **The Lakeflow Framework is deployed** — see Step 1 below and :doc:`deploy/before-you-deploy`
   - [ ] **Unity Catalog** enabled in your workspace
   - [ ] **UC catalog** already exists for sample deployment (default ``main``, or pass another with ``--catalog``) — the deploy scripts create schemas in that catalog, not the catalog itself
   - [ ] Familiarity with `Lakeflow Spark Declarative Pipelines <https://docs.databricks.com/aws/en/ldp/>`_ concepts (helpful, not required)
   - [ ] **The framework concepts are understood** — see :doc:`architecture/index`
   - [ ] **Autocomplete for Data Flow Specs** is configured — see :doc:`features/authoring/auto-complete`

Step 1 — Ensure the Lakeflow Framework is deployed
==================================================

Before creating a Pipeline Bundle, confirm the framework is **available in your target workspace** at a path you can reference as ``framework_source_path``. Either:

* **Central / platform-owned** — the platform team (or federated domain platform) has deployed the Framework Bundle to a shared workspace files location for your environment; obtain the path and version from them.
* **Developer-owned (local dev / POC)** — you deployed the framework yourself via :doc:`deploy/framework/local-framework`; the default path is under your user ``.bundle/.../files/src``.

Checklist:

* Framework files exist in the workspace
* You know the full ``framework_source_path`` (including target and version segment)
* ``databricks.yml`` in your pipeline bundle will reference that path

See :doc:`deploy/before-you-deploy` for deploy order and ownership. When pinning to a specific version, see :doc:`features/environments/versioning-framework`.

Step 2 — Create a new Pipeline Bundle
=====================================

Choose one of the following methods.

Copy the Pipeline Bundle template
---------------------------------

Copy the ``pipeline_bundle_template`` bundle from the root of the Framework repository.

Initialize a blank bundle with the Databricks CLI
--------------------------------------------------

.. note::

   Requires the Databricks CLI installed and configured. See the
   `Databricks CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_.

.. code-block:: console
   :class: lf-command-block

   databricks bundle init

This creates a DABs bundle similar to:

::

    my_pipeline_bundle/
    ├── fixtures/
    ├── resources/
    ├── scratch/
    │   ├── exploration.ipynb
    │   └── README.md
    ├── databricks.yml
    └── README.md

Adjust it to the Pipeline Bundle layout (directories only shown):

::

    my_pipeline_bundle/
    ├── fixtures/
    ├── resources/
    │   └── my_first_pipeline.yml
    ├── scratch/
    ├── src/
    │   ├── dataflows/
    │   ├── init/
    │   │   ├── pre/
    │   │   └── post/
    │   ├── libraries/
    │   ├── pipeline_configs/
    │   └── python/
    ├── databricks.yml
    └── README.md

Initialize from a custom template
---------------------------------

.. note::

   * Requires the Databricks CLI installed and configured.
   * Requires a custom template — see
     `custom bundle templates <https://docs.databricks.com/en/dev-tools/bundles/templates.html#use-a-custom-bundle-template>`_.
   * Custom templates should be maintained centrally; discuss with your platform team.

.. code-block:: console
   :class: lf-command-block

   databricks bundle init <path_to_custom_template_file>

Copy an existing Pipeline Bundle
--------------------------------

You can copy an existing Pipeline Bundle as a starting point. If you do:

* Reset targets and parameters in ``databricks.yml``
* Clear ``resources/``, ``src/dataflows/``, ``src/pipeline_configs/``, ``src/python/``,
  ``src/libraries/``, ``src/init/pre/``, and ``src/init/post/`` as needed

Step 3 — Update ``databricks.yml``
==================================

Adjust ``databricks.yml`` to include configurations similar to:

.. code-block:: yaml
   :linenos:

   bundle:
     name: bundle_name

   include:
     - resources/*.yml

   variables:
     owner:
       description: The owner of the bundle
       default: ${workspace.current_user.userName}
     catalog:
       description: The target UC catalog
       default: main
     schema:
       description: The target UC schema
       default: default
     layer:
       description: The target medallion layer
       default: bronze

   targets:
     dev:
       mode: development
       default: true
       workspace:
         host: https://<workspace>.databricks.com/
       variables:
         framework_source_path: /Workspace/Users/${var.owner}/.bundle/lakeflow_framework/dev/current/files/src

.. note::

   * ``framework_source_path`` must point to where the Lakeflow Framework bundle is deployed in the workspace.
   * By default the Framework Bundle deploys under the owner's
     ``.bundle/<project name>/<target environment>/<framework_version>/files/src`` path.
   * ``owner`` can be passed on the command line or via CI/CD so the path resolves in each deployment context.
     See :doc:`deploy/pipeline-bundle/local`.

Step 4 — Select your bundle structure
=====================================

Based on the use case and your org standards, choose a bundle structure.
See :doc:`bundle-structure`.

Step 5 — Select your Data Flow Spec format
==========================================

Choose the specification language / format for your org. See :doc:`features/metadata/spec-format`.

Keep in mind:

* The default format is JSON
* Format may already be enforced globally at the Framework level
* If enabled at Framework level, you can set format at the Pipeline Bundle level
* Do not mix formats in the same bundle

Step 6 — Set up substitutions (optional)
========================================

If you need substitutions and they are not already configured globally, set up your substitutions file.
See :doc:`features/metadata/substitutions`.

.. note::

   Optional — only required when the same pipeline bundle must deploy to multiple environments
   with different resource names. You can also do this later after Data Flow Specs exist.

Step 7 — Build your data flows
==============================

Repeat the following for each data flow.

Understand the use case
-----------------------

Decide:

* Data flow type: Standard, Flows or Materialized Views
* An existing pattern or a new design — see :doc:`patterns/index`

Consider:

* Which medallion layer the flow reads from and writes to
* Streaming vs batch
* Target table SCD0, SCD1, or SCD2
* Data quality rules
* Number of sources, join strategy, shared keys / sequence columns
* Transform type and complexity
* Latency / SLA requirements

Update substitutions
--------------------

Add any substitutions required for this data flow to the substitutions file.

Add init scripts (optional)
---------------------------

If the pipeline needs Spark configuration, event hooks, or one-time setup outside data-flow logic,
add ``.py`` scripts to:

* ``src/init/pre/`` — run **before** SDP data flow declarations
* ``src/init/post/`` — run **after** SDP data flow declarations

Scripts run in sorted filename order. Names starting with ``_`` are skipped.
Use a numeric prefix (for example ``01_setup.py``) to control order.
See :doc:`features/python/extensions`.

.. note::

   Optional — only when pipeline-level lifecycle setup is needed.

Build the Data Flow Spec
------------------------

Use the spec format you chose in **Step 5**. Then decide how to author the flow:

**Full Data Flow Spec** — write a complete spec file for this flow. Use when the flow is one-off or does not share structure with others in the bundle.

**Template-based spec** — define a reusable pattern once, then instantiate it with parameter sets when many flows differ only by table names, schemas, or similar parameters. See :doc:`features/metadata/templates`.

**Create a subdirectory** for the flow based on your bundle structure, under ``src/dataflows/`` if needed.

If using **templates**:

* Add a **template definition** under ``templates/`` (for example ``templates/<name>.json``) with parameters and the spec pattern
* Add a **template Data Flow Spec** that references the template and supplies one or more ``parameterSets`` — each set generates one runtime spec

If writing a **full spec**:

* Add the Data Flow Spec file(s) for the flow

Reference material:

* :doc:`spec-reference/index` — how to author the spec
* :doc:`features/metadata/templates` — template definitions and parameter sets
* :doc:`patterns/index` — high-level patterns and sample shapes
* :doc:`samples/index` — deploy samples to inspect working examples

**Create schema JSON / DDL file(s)** in the ``schemas`` subdirectory of the data flow home folder:

* Prefer an explicit schema for source and target tables (unless you want automatic Bronze schema evolution)
* Schemas are optional for staging tables
* Each schema in its own file, referenced from the Data Flow Spec

See :doc:`features/metadata/schema-management` for the schema specification.

**Create SQL transform file(s)** in the ``dml`` subdirectory when the flow uses transforms.

**Create data quality expectations file(s)** in the ``expectations`` subdirectory when needed.
See :doc:`features/data-quality/expectations`.

**Add pipeline logic modules** *(optional)* — if the spec references custom Python
(``pythonModule``, ``pythonTransform.module``, or a custom sink), add modules or packages under ``src/python/``.
The framework adds ``src/python/`` to ``sys.path`` at pipeline initialisation.
See :doc:`features/python/extensions`.

.. note::

   Optional — only when the Data Flow Spec references a custom Python module.

Step 8 — Create pipeline definitions
====================================

After pipeline definitions are authored, deploy the bundle — see :doc:`deploy/index`.

Define Spark Declarative Pipelines as YAML under ``resources/``. Each pipeline has its own file.
DABs uses these files to create pipelines in the target workspace.

How many resource files you create depends on the bundle structure you selected.

Create a resource YAML file
---------------------------

Add a new YAML file in ``resources/``, named after the pipeline.

Add the base YAML definition
----------------------------

Replace ``<value>`` placeholders on the highlighted lines:

.. code-block:: yaml
   :linenos:
   :emphasize-lines: 3, 4

   resources:
     pipelines:
       <value_pipeline_name>:
         name: <value_pipeline_name>
         catalog: ${var.catalog}
         schema: ${var.schema}
         channel: CURRENT
         serverless: true
         libraries:
           - notebook:
               path: ${var.framework_source_path}/dlt_pipeline

         configuration:
           bundle.sourcePath: /Workspace/${workspace.file_path}/src
           framework.sourcePath: /Workspace/${var.framework_source_path}
           workspace.host: ${workspace.host}
           bundle.target: ${bundle.target}
           pipeline.layer: ${var.layer}

Add Data Flow filters (optional)
--------------------------------

By default a pipeline executes all data flows in the bundle. When you define multiple pipelines,
filter which flows each pipeline runs:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Configuration option
     - Description
   * - ``pipeline.dataFlowIdFilter``
     - Data flow ID(s) to include
   * - ``pipeline.dataFlowGroupFilter``
     - Data flow group(s) to include
   * - ``pipeline.flowGroupIdFilter``
     - Flow group ID(s) within a data flow to include
   * - ``pipeline.fileFilter``
     - File path for the data flow to include
   * - ``pipeline.targetTableFiler``
     - Target table(s) to include

.. note::

   Filter values can be a single value or a comma-separated list.

Example with filters:

.. code-block:: yaml
   :linenos:
   :emphasize-lines: 19-22

   resources:
     pipelines:
       <value_pipeline_name>:
         name: <value_pipeline_name>
         catalog: ${var.catalog}
         schema: ${var.schema}
         channel: CURRENT
         serverless: true
         libraries:
           - notebook:
               path: ${var.framework_source_path}/dlt_pipeline

         configuration:
           bundle.sourcePath: /Workspace/${workspace.file_path}/src
           framework.sourcePath: /Workspace/${var.framework_source_path}
           workspace.host: ${workspace.host}
           bundle.target: ${bundle.target}
           pipeline.layer: ${var.layer}
           pipeline.targetTableFiler: <value_target_table>
           pipeline.dataFlowIdFilter: <value_flow_id>
           pipeline.flowGroupIdFilter: <value_flow_group_id>
           pipeline.fileFilter: <value_file_path>

Add cluster libraries (optional)
--------------------------------

Install third-party or in-house packages via ``environment.dependencies`` in the pipeline resource YAML.
See :doc:`features/python/extensions`. Sources include:

* **PyPI** — ``- my_package>=1.0``
* **UC Volumes** — ``- /Volumes/catalog/schema/my_pkg.whl``
* **Artifact repository** — ``- https://artifactory.example.com/my_pkg.whl``
* **Bundle wheel** — ``- /Workspace/${workspace.file_path}/src/libraries/my_package.whl``

For bundle wheels, place the ``.whl`` in ``src/libraries/``. You may also put loose ``.py`` files
there when they must be on ``sys.path`` without being spec-referenced.
