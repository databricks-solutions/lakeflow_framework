Building a Pipeline Bundle
##########################

Prerequisites
=============

- The Lakeflow Framework must be deployed. See :doc:`deploy_framework` for details.
- Ensure you have autocomplete for Data Flow Specs configured. See :doc:`feature_auto_complete` for details.
- Understanding of the core concepts of the Framework. See :doc:`concepts` for details.

Steps to build a Pipeline Bundle
================================

1. Create a new Pipeline Bundle
-------------------------------

A new Pipeline Bundle can be created using the following methods.

* **Copy Pipeline Bundle Template:**
  
  You can copy the ``pipeline_bundle_template`` bundle provided with the framework. The bundle is located in the root directory of the Framework Repository.

* **Databricks CLI - Initialize Blank Bundle:**

  .. note:: 
      The following steps assume that you have the Databricks CLI installed and configured. If not, please refer to the `Databricks CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_.

  You can create a new DABs bundle from the command line by executing the command:

  .. code-block:: bash

      databricks bundle init

  This will create a new DABs bundle with the following structure:

  ::

      my_pipeline_bundle/
      ├── fixtures/
      ├── resources/
      ├── scratch/
      │   ├── exploration.ipynb
      │   └── README.md
      ├── databricks.yml
      └── README.md


  Modify the bundle to have the following structure without the files:

  ::

      my_pipeline_bundle/
      ├── fixtures/
      ├── resources/
      │   └── my_first_pipeline.yml
      ├── scratch/
      ├── src/
      │   ├── dataflows
      │   └── pipeline_configs
      ├── databricks.yml
      └── README.md

* **Databricks CLI - Initialize Bundle Using a Custom Template:**

  .. note:: 
      This method assumes that:
        * You have the Databricks CLI installed and configured. If not, please refer to the `Databricks CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_.
        * You have a custom template file that you want to use to initialize the bundle. Refer to the `Databricks CLI documentation <https://https://docs.databricks.com/en/dev-tools/bundles/templates.html#use-a-custom-bundle-template>`_ for more information on how to create a custom template.
        * A custom template should be maintained centrally, discuss this with your platform team.

  You can create a new DABs bundle from the command line by executing the command:

  .. code-block:: bash

      databricks bundle init <path_to_custom_template_file>

* **Copy an Existing Pipeline Bundle:**

  You can always copy an existing Pipeline Bundle to use as a starting point for a new Pipeline Bundle. If doing this bear in mind that you may need to:

  - Reset the targets and parameter in the ``databricks.yml`` file
  - Clean out the following folders: ``resources``, ``src/dataflows`` and ``src/pipeline_configs``

2. Update the ``databricks.yml`` File
-------------------------------------

The databricks.yml needs to be adjusted to include the following configurations:

.. code-block:: yaml

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
        framework_source_path: /Workspace/Users/${var.owner}/.bundle/nab_dlt_framework/dev/files/src

.. note::
    * The ``framework_source_path`` variable should point to the location of where the Lakeflow Framework bundle is deployed in the Databricks workspace. 
    * By default the Lakeflow Framework Bundle is deployed to the owner's (person deploying the bundle) workspace files how folder under the ``.bundle/<project name>/<target environment>/files/`` directory.
    * The ``owner`` can either be passed via the command line or via your CI/CD tool to allow deployment to the appropriate workspace files location in the given deployment context. See the :doc:`deploy_pipeline_bundle` section for more information.

3. Select your Bundle Structure
-------------------------------

Based on the Use Case and the standards defined in your Org, select the appropriate bundle structure. See the :doc:`build_pipeline_bundle_structure` section for guidance.

4. Select your Data Flow Specification Language / Format
-------------------------------------------------------

Based on the implementation and standards in your Org, you can select the appropriate specification language / format. See the :doc:`feature_spec_format` section details.

Be aware that:
- The default format is `JSON`.
- The format may have alrteady been enforced globally at Framework level per you orgs standards.
- If enabled at Framework level, you can set the format at the Pipeline Bundle level.
- You cannot mix and match formats in the same bundle, it's important to ensure consistency for engineers working on the same bundle.

5. Setup your Substitutions Configuration
-----------------------------------------

If you haven't already done so, familiarize yourself with the :doc:`feature_substitutions` feature of the Framework.

If you need to use substitutions and the substitutions you require have not been configure globally at the Framework level, you need to now setup your substitutions file. See the :doc:`substitutions` section for guidance.

.. note::
    This step is optional and only required if substitutions are required to deploy the same pipeline bundle to multiple environments with different resources names. This step can also be actioned later in the build process after the Data Flow Specs have been created.

6. Build your Data Flows
------------------------

Iterate over the following steps to create each individual Data Flow:

1. **Understand your Use Case:**

  In this step you will need to make two selections:
    a. The Data Flow Type: Standard or Flows
    #. Select from an existing pattern or create a new one. Refer to the :doc:`patterns` section for more information on the different patterns.

  To make these selections you need to consider the following:
    a. What layer of the Lakehouse will the Data Flow read from and write to?
    #. Is this a streaming or batch data flow?
    #. Is my target table SCD0, SCD1 or SCD2?
    #. Are there Data Quality rules that need to be applied to the data?
    #. How many source tables are there, what join strategy is require and do the tables share common keys and sequence columns?
    #. Are there any transformations required and if so what type and complexity?
    #. What are the latency / SLA requirements?

2. **Update your Substitutions Configuration:**

  If necessary add any substitutions required for your Data Flow to the substitutions file.

3. **Build the Data Flow Spec:**

  a. Create a sub-directory per you selected bundle structure:

    If necessary, create a new folder in the ``src/dataflows`` directory based on your selected bundle strategy.
  
  b. Create Data Flow Spec file(s):
    * Refer to the :doc:`dataflow_spec_reference` section to build your Data Flow Spec
    * Refer to the :doc:`patterns` section for high level patterns and sample code.
    * Refer to the :doc:`deploy_samples` section on how to deploy the samples so you can reference the sample code.

  c. Create schema JSON / DDL files(s):
  
    Create your schema JSON / DDL files in the ``schema`` sub-directory of your Data Flow Spec's home folder:
      
      * You should in general always specify a schema for your source and target tables, unless you want schema evolution to happen automatically in Bronze.
      * Schemas are optional for staging tables.
      * Each schema must be defined in it's own individual file.
      * Each schema must be referenced by the appropriate object(s) in your Data Flow Spec JSON file(s).

    A schema file must have a format similar to the below example:

    The schema specification can be found in the :doc:`feature_schemas` section.

    d. Create SQL Transform file(s):

      If you have transforms in your Data Flow, you will need to create a SQL file for each transform, in the ``dml`` sub-directory of your Data Flow Spec's home folder.

    e. Create Data Quality Expectations file(s):

      If you have data quality expectations in your Data Flow, you will need to create an expectations file for your target table in the ``expectations`` sub-directory of your Data Flow Spec's home folder.

      Refer to the :doc:`feature_data_quality_expectations` section for guidance on how to create an expectations file.

7. Create your Pipeline Definitions
-----------------------------------

Spark Declarative Pipelines are defined in the ``resources`` directory. Each Pipeline is defined in it's own individual YAML file.

DAB's will use these YAML files to create the Spark Declarative Pipelines in the target Databricks Workspace.

How many pipeline resource files you create and how you configure them will be based on the Bundle Structure you have selected.

To create a single Pipeline definition, follow these steps:

1. **Create a resource YAML file:**

  Create a new YAML file in the ``resources`` directory. Name it after the Pipeline you want to create.

2. **Add the Base YAML Definition:**

  Add the following base content to the file, replacing the ``<value>`` tags in the highlighted rows with the appropriate values for your Pipeline.
  
  .. code-block:: yaml
    :emphasize-lines: 3, 4

      resources:
        pipelines:
          <value_pipeline_name>:
            name:  <value_pipeline_name>
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

3. **Add any required Data Flow filters:**

  By default, if you don't specify any Data Flow filters, the pipleine will execute all Data Flows in you Pipeline Bundle.

  If you are creating more than one Pipeline definition in your bundle, you may want your Pipeline(s) to only execute specific Data Flows. 

  The Framework provides number of ways to filter the Data Flows a pipeline executes. These can be set per the configuration options described below:

  .. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Configuration Option
      - Description
    * - ``pipeline.dataFlowIdFilter``
      - The ID(s) of the data flow to include in the pipeline
    * - ``pipeline.dataFlowGroupFilter``
      - The data flow group(s) to include in the pipeline
    * - ``pipeline.flowGroupIdFilter``
      - The ID's of the flow group(s), in a data flow, to include in the pipeline
    * - ``pipeline.fileFilter``
      - The file path for the data flow to include in the pipeline
    * - ``pipeline.targetTableFiler``
      - The target table(s) to include in the pipeline

  .. note::
      For all the above filter fields, the values can be a single value or multiple values separated by a comma.

  You can add the appropriate Data Flow filter options described above to the Pipeline definition, as show below:

  .. code-block:: yaml
    :emphasize-lines: 20-23

      resources:
        pipelines:
          <value_pipeline_name>:
            name:  <value_pipeline_name>
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
