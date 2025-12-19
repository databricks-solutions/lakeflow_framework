Spark Configuration
==================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Framework Bundle` :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Global` :bdg-success:`Pipeline`
   * - **Databricks Docs:**
     - https://spark.apache.org/docs/latest/configuration.html

The Spark Configuration feature allows you to define and manage Spark configurations either globally at framework level across all pipelines or at pipeline bundle level. 

Configuration
-------------

| **Scope: Global**
| In the Framework bundle, Spark configurations are defined in the global configuration file located at: ``src/config/global.json|yaml`` under the ``spark_config`` section.

| **Scope: Bundle**
| In a Pipeline bundle, Spark configurations are defined in the global configuration file located at: ``src/pipeline_configs/global.json|yaml`` under the ``spark_config`` section.

Configuration Schema
--------------------

The Spark configuration section must follow this schema:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "spark_config": {
                 "<configuration_key>": "<configuration_value>",
                 ...
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         spark_config:
           <configuration_key>: <configuration_value>
           ...

.. list-table::
   :header-rows: 1

   * - Field
     - Description
   * - **configuration_key**
     - The Spark configuration property name (e.g., "spark.sql.shuffle.partitions")
   * - **configuration_value**
     - The value to set for the configuration property. Can be string, number, or boolean depending on the property.

Common Configuration Properties
-----------------------------

Here are some commonly used Spark configuration properties:

.. list-table::
   :header-rows: 1

   * - Property
     - Description
     - Default Value
   * - **spark.sql.shuffle.partitions**
     - Number of partitions to use for shuffle operations
     - 200
   * - **spark.sql.files.maxPartitionBytes**
     - Maximum size of a partition during file read
     - 128MB
   * - **spark.sql.adaptive.enabled**
     - Enable adaptive query execution
     - true
   * - **spark.sql.broadcastTimeout**
     - Timeout in seconds for broadcast joins
     - 300

Example Configuration
-------------------

Below is an example of a typical Spark configuration in the `global.json|yaml` file:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "spark_config": {
                 "spark.sql.shuffle.partitions": "200",
                 "spark.sql.adaptive.enabled": "true",
                 "spark.sql.files.maxPartitionBytes": "134217728",
                 "spark.sql.broadcastTimeout": "300"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         spark_config:
           spark.sql.shuffle.partitions: '200'
           spark.sql.adaptive.enabled: 'true'
           spark.sql.files.maxPartitionBytes: '134217728'
           spark.sql.broadcastTimeout: '300'

.. admonition:: Best Practice
   :class: note
    
    * Start with the default Spark configurations and adjust based on your specific workload needs
    * Monitor query performance and resource utilization to optimize configurations
    * Document any non-standard configuration changes and their rationale
    * Test configuration changes in development before applying to production

.. Note::
    Some Spark configurations may be overridden by Databricks cluster configurations or job-specific settings. Refer to the Databricks documentation for the configuration precedence rules.

Advanced Usage
-------------

Dynamic Configuration
^^^^^^^^^^^^^^^^^^^

For certain use cases, you may want to set different Spark configurations based on the environment or workload. This can be achieved using environment variables or the substitutions feature of the framework.

Example with environment-specific configurations:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "spark_config": {
                 "spark.sql.shuffle.partitions": "${SHUFFLE_PARTITIONS}",
                 "spark.sql.adaptive.enabled": "${ADAPTIVE_EXECUTION_ENABLED}"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         spark_config:
           spark.sql.shuffle.partitions: ${SHUFFLE_PARTITIONS}
           spark.sql.adaptive.enabled: ${ADAPTIVE_EXECUTION_ENABLED}

Performance Tuning
^^^^^^^^^^^^^^^^

When tuning Spark configurations for performance:

1. Start with the defaults
2. Monitor query performance and resource utilization
3. Identify bottlenecks
4. Adjust relevant configurations
5. Test and measure impact
6. Document successful optimizations

.. admonition:: Important
   :class: warning
    
    Incorrect Spark configurations can significantly impact performance and stability. Always test configuration changes in a development environment first. 