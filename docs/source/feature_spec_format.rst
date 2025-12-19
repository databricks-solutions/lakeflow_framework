Data Flow Specification Format
==============================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Framework` :bdg-info:`Pipeline`

Overview
--------
The Framework supports both JSON and YAML formats for defining pipeline specifications, providing flexibility in how you author and maintain your data flow specs, substitution files, secrets files, and other configuration files.

.. important::

    The specification format applies to all configuration files in a Pipeline Bundle, including:
    
    - Data flow specifications (main specs and flow groups)
    - Data quality expectations
    - Substitution files
    - Secrets files

This feature allows development teams to choose the format that best suits their workflow and preferences, while maintaining full compatibility with the Framework's validation and execution capabilities.

.. note::

    Both formats are functionally equivalent and fully interchangeable. The choice between JSON and YAML is purely a matter of preference and workflow requirements.

Configuration
-------------

The specification format can be configured at two levels:

1. **Framework Level**: Global configuration that applies to all Pipeline Bundles
2. **Pipeline Level**: Pipeline-specific configuration that can override the global setting (if allowed)

Framework-Level Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| **Scope: Framework**
| The global specification format is defined in the Framework's global configuration file: ``src/config/global.json|yaml``

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "pipeline_bundle_spec_format": {
                 "format": "json",
                 "allow_override": false
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         pipeline_bundle_spec_format:
           format: json
           allow_override: false

.. list-table::
   :header-rows: 1

   * - Field
     - Description
     - Valid Values
     - Default
   * - **format**
     - The default specification format for all Pipeline Bundles
     - ``"json"`` or ``"yaml"``
     - ``"json"``
   * - **allow_override**
     - Whether individual Pipeline Bundles can override the global format setting
     - ``true`` or ``false``
     - ``false``

Pipeline-Level Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| **Scope: Pipeline**
| In a Pipeline Bundle, the specification format can be set in the pipeline configuration file: ``src/pipeline_configs/global.json|yaml``

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "pipeline_bundle_spec_format": {
                 "format": "yaml"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         pipeline_bundle_spec_format:
           format: yaml

.. important::

    Pipeline-level overrides are only permitted if ``allow_override`` is set to ``true`` in the Framework's global configuration. If ``allow_override`` is ``false``, attempting to override the format will result in a validation error.

Supported File Types and Naming Conventions
--------------------------------------------

The Framework automatically detects the specification format based on file naming conventions:

JSON Format
^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - File Type
     - File Suffix
   * - **Main Specifications**
     - ``*_main.json``
   * - **Flow Group Specifications**
     - ``*_flow.json``
   * - **Data Quality Expectations**
     - ``*_dqe.json``
   * - **Secrets Files**
     - ``*_secrets.json``
   * - **Substitution Files**
     - ``*_substitutions.json``

YAML Format
^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - File Type
     - File Suffix
   * - **Main Specifications**
     - ``*_main.yaml`` or ``*_main.yml``
   * - **Flow Group Specifications**
     - ``*_flow.yaml`` or ``*_flow.yml``
   * - **Data Quality Expectations**
     - ``*_expectations.yaml`` or ``*_expectations.yml``
   * - **Secrets Files**
     - ``*_secrets.yaml`` or ``*_secrets.yml``
   * - **Substitution Files**
     - ``*_substitutions.yaml`` or ``*_substitutions.yml``

.. note::

    The Framework supports both ``.yaml`` and ``.yml`` extensions for YAML files. Use whichever convention your team prefers, but be consistent within a Pipeline Bundle.

Example Specification
----------------------

The following example shows a data flow specification in both JSON and YAML formats:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "dataFlowId": "customer_main",
             "dataFlowGroup": "customers",
             "dataFlowType": "standard",
             "sourceSystem": "sourceA",
             "sourceType": "autoloader",
             "sourceFormat": "json",
             "sourceDetails": {
                 "path": "${base_data_dir}/customer_data",
                 "readerOptions": {
                     "cloudFiles.format": "json",
                     "cloudFiles.inferColumnTypes": "true"
                 }
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "customer",
                 "tableProperties": {
                     "delta.enableChangeDataFeed": "true"
                 }
             },
             "dataQualityExpectationsEnabled": true,
             "quarantineMode": "on"
         }

   .. tab:: YAML

      .. code-block:: yaml

         dataFlowId: customer_main
         dataFlowGroup: customers
         dataFlowType: standard
         sourceSystem: sourceA
         sourceType: autoloader
         sourceFormat: json
         sourceDetails:
           path: ${base_data_dir}/customer_data
           readerOptions:
             cloudFiles.format: json
             cloudFiles.inferColumnTypes: 'true'
         mode: stream
         targetFormat: delta
         targetDetails:
           table: customer
           tableProperties:
             delta.enableChangeDataFeed: 'true'
         dataQualityExpectationsEnabled: true
         quarantineMode: on

Best Practices
--------------

1. **Choose One Format Globally**: While technically possible to mix formats across Bundles, it's recommended to standardise on a single format.

2. **Version Control Considerations**: YAML may produce cleaner diffs in version control systems due to its more human-readable format and lack of trailing commas.

3. **Validation**: Always validate specifications after conversion or manual edits using the Framework's built-in validation capabilities.

4. **Schema Files**: Schema files (``*_schema.json``) remain in JSON or DDL format regardless of the specification format setting, as JSON is the format for schema definitions.

Configuration Examples
----------------------

Example 1: Framework Enforces JSON Format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Framework Configuration** (``src/config/global.json|yaml``):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "pipeline_bundle_spec_format": {
                 "format": "json",
                 "allow_override": false
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         pipeline_bundle_spec_format:
           format: json
           allow_override: false

**Result**: All Pipeline Bundles must use JSON format. Pipeline-level overrides will be rejected.

Example 2: Framework Allows Format Flexibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Framework Configuration** (``src/config/global.json|yaml``):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "pipeline_bundle_spec_format": {
                 "format": "json",
                 "allow_override": true
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         pipeline_bundle_spec_format:
           format: json
           allow_override: true

**Pipeline Configuration** (``src/pipeline_configs/global.json|yaml``):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "pipeline_bundle_spec_format": {
                 "format": "yaml"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         pipeline_bundle_spec_format:
           format: yaml

**Result**: This specific Pipeline Bundle will use YAML format, while other bundles will default to JSON unless explicitly overridden.

Example 3: Framework Defaults to YAML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Framework Configuration** (``src/config/global.json|yaml``):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "pipeline_bundle_spec_format": {
                 "format": "yaml",
                 "allow_override": false
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         pipeline_bundle_spec_format:
           format: yaml
           allow_override: false

**Result**: All Pipeline Bundles must use YAML format. This is useful when migrating an entire organization to YAML.

Troubleshooting
---------------

Format Mismatch Errors
^^^^^^^^^^^^^^^^^^^^^^
**Problem**: Framework reports that files cannot be found or loaded.

**Solution**:
- Verify the ``format`` setting in both Framework and Pipeline configurations
- Ensure file suffixes match the configured format (e.g., ``*_main.yaml`` for YAML)
- Check that all files in the bundle use consistent naming conventions

Override Not Permitted
^^^^^^^^^^^^^^^^^^^^^^
**Problem**: Error message: "Pipeline bundle spec format has been set at global framework level. Override has been disabled."

**Solution**:
- This occurs when attempting to override the format at Pipeline level when ``allow_override`` is ``false``
- Either remove the Pipeline-level configuration or request that ``allow_override`` be enabled in the Framework configuration

Invalid Format Value
^^^^^^^^^^^^^^^^^^^^
**Problem**: Error message: "Invalid pipeline bundle spec format: <value>"

**Solution**:
- Ensure the ``format`` field is set to either ``"json"`` or ``"yaml"``
- Check for typos in the configuration file
- Validate the JSON syntax of the configuration file

Validation Errors After Conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Problem**: YAML files fail validation after conversion from JSON.

**Solution**:
- Validate the YAML syntax and structure
- Check for data type issues (e.g., boolean values should be ``true``/``false``, not strings)
- Ensure quotes are preserved around string values that look like other types (e.g., ``"true"`` vs ``true``)
- Review the specification for any structural issues

Mixed Format Detection
^^^^^^^^^^^^^^^^^^^^^^
**Problem**: Bundle contains both JSON and YAML files with the same base name.

**Solution**:
- The Framework will load files based on the configured format
- Remove files that don't match the configured format to avoid confusion
- Ensure consistent naming conventions throughout the bundle

See Also
--------
- :doc:`feature_substitutions` - Using substitutions in specifications
- :doc:`feature_secrets` - Managing secrets in specifications  
- :doc:`feature_validation` - Specification validation

