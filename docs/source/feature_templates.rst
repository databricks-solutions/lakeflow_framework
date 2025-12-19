Templates
=========

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Pipeline`

Overview
--------
The Dataflow Spec Templates feature allows data engineers to create reusable templates for dataflow specifications. This significantly reduces code duplication when multiple dataflows share similar structures but differ only in specific parameters (e.g., table names, columns, etc.).

.. important::

    Templates provide a powerful mechanism for standardizing dataflow patterns across your organization while maintaining flexibility for specific implementations.

This feature allows development teams to:

- **Reduce Code Duplication**: Write once, reuse many times
- **Ensure Consistency**: Similar dataflows follow the same structure  
- **Improve Productivity**: Quickly create multiple similar specifications
- **Reduce Errors**: Less copy-paste reduces human error
- **Make Patterns Explicit**: Templates make organizational patterns discoverable

.. note::

    Template processing happens during the initialization phase of pipeline execution as the dataflow specs are loaded. Each processed spec is validated using the standard validation process.

How It Works
------------

The template system consists of three main components:

1. **Template Definitions**: JSON files containing template definitions with placeholders
2. **Template Dataflow Specifications**: A dataflow specification that references a template and provides parameter sets
3. **Template Processing**: Framework logic that processes the template dataflow specifications and generates one dataflow spec per parameter set.


Anatomy of a Template Definition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A template definition is a JSON file that defines a reusable dataflow pattern. It consists of three main components:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "name": "standard_cdc_template",
             "parameters": {
                 "dataFlowId": {
                     "type": "string",
                     "required": true
                 },
                 "sourceDatabase": {
                     "type": "string",
                     "required": true
                 },
                 "sourceTable": {
                     "type": "string",
                     "required": true
                 },
                 "targetTable": {
                     "type": "string",
                     "required": true
                 }
             },
             "template": {
                 "dataFlowId": "${param.dataFlowId}",
                 "sourceDetails": {
                     "database": "${param.sourceDatabase}",
                     "table": "${param.sourceTable}"
                 },
                 "targetDetails": {
                     "table": "${param.targetTable}"
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         name: standard_cdc_template
         parameters:
           dataFlowId:
             type: string
             required: true
           sourceDatabase:
             type: string
             required: true
           sourceTable:
             type: string
             required: true
           targetTable:
             type: string
             required: true
         template:
           dataFlowId: ${param.dataFlowId}
           sourceDetails:
             database: ${param.sourceDatabase}
             table: ${param.sourceTable}
           targetDetails:
             table: ${param.targetTable}

**Key Components:**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Component
     - Description
   * - **name**
     - The unique name for the template. make this the same as the filename. This is currently a placeholder for future functiuonality.
   * - **parameters**
     - An object defining all parameters that can be used in the template. Each parameter has a ``type`` (string, list, object, integer, boolean) and ``required`` flag (defaults to true). Optional ``default`` values can be specified.
   * - **template**
     - The dataflow specification template containing placeholders in the format ``${param.<key>}``; where ``<key>`` is the name of a parameter defined in the ``parameters`` object. This can be any valid dataflow specification structure with parameters substituted at processing time.

.. important::

    - placeholders can be used in both keys, as full values or as part of or a full string value.
    - in JSON specs placeholders must always be wrapped in quotes: ``"${param.name}"``

**File Location:**
- Template definitions: ``<dataflow_base_path>/templates/<name>.json`


Anatomy of a Template Dataflow Specification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A template dataflow specification is a simplified file that references a template and provides parameter sets for instantiation. Instead of writing full dataflow specs, data engineers create a template reference:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "template": "standard_cdc_template",
             "parameterSets": [
                 {
                     "dataFlowId": "customer_scd2",
                     "sourceDatabase": "{bronze_schema}",
                     "sourceTable": "customer_raw",
                     "targetTable": "customer_scd2"
                 },
                 {
                     "dataFlowId": "customer_address_scd2",
                     "sourceDatabase": "{bronze_schema}",
                     "sourceTable": "customer_address_raw",
                     "targetTable": "customer_address_scd2"
                 }
             ]
         }

   .. tab:: YAML

      .. code-block:: yaml

         template: standard_cdc_template
         parameterSets:
           - dataFlowId: customer_scd2
             sourceDatabase: '{bronze_schema}'
             sourceTable: customer_raw
             targetTable: customer_scd2
           - dataFlowId: customer_address_scd2
             sourceDatabase: '{bronze_schema}'
             sourceTable: customer_address_raw
             targetTable: customer_address_scd2

**Key Components:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Component
     - Description
   * - **template**
     - The filename of the template definition to use (without the ``.json`` extension). The framework will search for this template in the configured template directories.
   * - **parameterSets**
     - An array of parameter sets. Each object in the array represents one set of parameter values that will generate one complete dataflow specification. Each parameter set must include all required parameters defined in the template definition.

.. important::

    - Each parameter set must include a unique ``dataFlowId`` value
    - The array must contain at least one parameter set
    - All required parameters from the template definition must be provided in each parameter set

**File Location:**

Template dataflow specifications follow the standard dataflow specification naming convention: ``<dataflow_base_path>/dataflows/<dataflow_name>/dataflowspec/*_main.json``

**Processing Result:**

A template dataflow specification with N parameter sets will generate N complete dataflow specifications at runtime, each validated independently.  

Template Processing
^^^^^^^^^^^^^^^^^

During the dataflow spec build process, the template processor will:

1. Detect spec files containing a ``template`` key
2. Loads the referenced template file
3. For each parameter set in ``parameterSets``, create a concrete spec by replacing all ``${param.<key>}`` placeholders
4. Validate each expanded spec using the existing schema validators
5. Return the expanded specs with unique internal identifiers

Example Usage
-------------

Example: Basic File Source Ingestion Template
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example shows a template for basic file source ingestion, from a hypothetical source system called "erp_system".

**Template Definition** (``src/templates/bronze_erp_system_file_ingestion_template.json|yaml``):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "name": "bronze_erp_system_file_ingestion_template",
             "parameters": {
                 "dataFlowId": {
                     "type": "string",
                     "required": true
                 },
                 "sourceTable": {
                     "type": "string",
                     "required": true
                 },
                 "schemaPath": {
                     "type": "string",
                     "required": true
                 },
                 "targetTable": {
                     "type": "string",
                     "required": true
                 }
             },
             "template": {
                 "dataFlowId": "${param.dataFlowId}",
                 "dataFlowGroup": "bronze_erp_system",
                 "dataFlowType": "standard",
                 "sourceSystem": "erp_system",
                 "sourceType": "cloudFiles",
                 "sourceViewName": "v_${param.sourceTable}",
                 "sourceDetails": {
                     "path": "{landing_erp_file_location}/${param.sourceTable}/",
                     "readerOptions": {
                         "cloudFiles.format": "csv",
                         "header": "true"
                     },
                     "schemaPath": "${param.schemaPath}"
                 },
                 "mode": "stream",
                 "targetFormat": "delta",
                 "targetDetails": {
                     "table": "${param.targetTable}"
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         name: bronze_erp_system_file_ingestion_template
         parameters:
           dataFlowId:
             type: string
             required: true
           sourceTable:
             type: string
             required: true
           schemaPath:
             type: string
             required: true
           targetTable:
             type: string
             required: true
         template:
           dataFlowId: ${param.dataFlowId}
           dataFlowGroup: bronze_erp_system
           dataFlowType: standard
           sourceSystem: erp_system
           sourceType: cloudFiles
           sourceViewName: v_${param.sourceTable}
           sourceDetails:
             path: '{landing_erp_file_location}/${param.sourceTable}/'
             readerOptions:
               cloudFiles.format: csv
               header: 'true'
             schemaPath: ${param.schemaPath}
           mode: stream
           targetFormat: delta
           targetDetails:
             table: ${param.targetTable}

**Template Dataflow Specification** (``src/dataflows/bronze_erp_system/dataflowspec/bronze_erp_system_file_ingestion_main.json|yaml``):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "template": "bronze_erp_system_file_ingestion_template",
             "parameterSets": [
                 {
                     "dataFlowId": "customer_file_source",
                     "sourceTable": "customer",
                     "schemaPath": "customer_schema.json",
                     "targetTable": "customer"
                 },
                 {
                     "dataFlowId": "customer_address_file_source",
                     "sourceTable": "customer_address",
                     "schemaPath": "customer_address_schema.json",
                     "targetTable": "customer_address"
                 },
                 {
                     "dataFlowId": "supplier_file_source",
                     "sourceTable": "supplier",
                     "schemaPath": "supplier_schema.json",
                     "targetTable": "supplier"
                 }
             ]
         }

   .. tab:: YAML

      .. code-block:: yaml

         template: bronze_erp_system_file_ingestion_template
         parameterSets:
           - dataFlowId: customer_file_source
             sourceTable: customer
             schemaPath: customer_schema.json
             targetTable: customer
           - dataFlowId: customer_address_file_source
             sourceTable: customer_address
             schemaPath: customer_address_schema.json
             targetTable: customer_address
           - dataFlowId: supplier_file_source
             sourceTable: supplier
             schemaPath: supplier_schema.json
             targetTable: supplier

**Result**: This template dataflow specification generates **3 concrete dataflow specs**, one for each parameter set in the ``parameterSets`` array.


Parameter Types
---------------

Parameters support multiple data types and structures:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Type
     - Template Usage
     - Example
   * - **Strings**
     - ``"${param.tableName}"``
     - ``"tableName": "customer"``
   * - **Numbers**
     - ``${param.batchSize}``
     - ``"batchSize": 1000``
   * - **Booleans**
     - ``${param.enabled}``
     - ``"enabled": true``
   * - **Arrays**
     - ``${param.keyColumns}``
     - ``"keyColumns": ["ID", "DATE"]``
   * - **Objects**
     - ``${param.config}``
     - ``"config": {"key": "value"}``

Key Features
------------

Python Function Path Search Priority
^^^^^^^^^^^^^^^^^^^^^^^^^

Enhanced fallback chain for path values.

The framework searches for python function path values in the following order:

1. In the pipeline bundle base path of the dataflow spec file
2. Under the templates directory of the pipeline bundle
3. Under the extensions directory of the pipeline bundle
4. Under the framework extensions directory

Error Handling
^^^^^^^^^^^^^^

The framework provides clear error messages for common issues:

- **Missing template file**: Lists all searched locations
- **Missing parameters**: Warns about unreplaced placeholders
- **Invalid JSON**: Shows parsing errors with context
- **Validation errors**: Each expanded spec is validated individually

Validation
^^^^^^^^^^

Each expanded spec is validated using the existing schema validators to ensure correctness.

Template usage specs are validated against the schema at ``src/schemas/spec_template.json``:

- ``template``: Required string (template name without .json extension)
- ``params``: Required array with at least one parameter object
- Each parameter object must be a dictionary with at least one key-value pair

Unique Identifiers
^^^^^^^^^^^^^^^^^^

Generated specs receive unique internal keys in the format ``path#template_0``, ``path#template_1``, etc., to ensure proper tracking and debugging.

Best Practices
--------------

Naming Conventions
^^^^^^^^^^^^^^^^^^

1. **Template Files**: Use descriptive names ending with ``_template`` (e.g., ``standard_cdc_template.json``)
2. **Parameter Names**: Use clear, descriptive names (e.g., ``sourceTable`` instead of ``st``)
3. **Consistency**: Maintain consistent naming patterns across related templates

Development and Testing
^^^^^^^^^^^^^^^^^^^^^^^

1. **Concrete First**: Develop a concrete dataflow spec first, get it working and then turn it into a template defintion.
1. **Validation**: Always test processed specs by running the pipeline with a small subset of data
2. **Version Control**: Track templates in version control to maintain a history of changes
3. **Iterative Development**: Start with a simple template and enhance it as patterns emerge

Maintainability
^^^^^^^^^^^^^^^

1. **Template Updates**: When updating a template, test all usages to ensure compatibility
2. **Parameter Validation**: Document required parameters for each template
3. **Backwards Compatibility**: Consider versioning templates if making breaking changes

Limitations
-----------

The current template implementation has the following limitations, which may be addressed in future versions:

1. **No Template Sub Components (Blocks)**: Templates cannot reference other templates or smaller template blocks
2. **No Conditional Logic**: Complex conditional logic is not supported (consider using multiple templates)

.. note::

    For complex conditional logic requirements, create multiple templates that represent different scenarios rather than trying to implement logic within a single template.
