Secrets Management
==================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Pipeline`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/security/secrets

Overview
--------
Databricks natively supports secrets management and the secure retrieval of credentials, connection details, host names or 
other sensitive information for use at pipeline execution time. This negates the need to include these details directly in your data flow specs, config files or code.

.. important::

    Credentials and other sensitive information should never be hardcoded in your data flow specs, config files or code. 
    Use the native Databricks secrets management features to store and retrieve these details.

The Framework allows you to specify the Secret Scopes and Secrets you need access to at Pipeline Bundle level and then reference these in your data flow specs.

.. important::

    Secret management is implemented in a such a way that:
    
    - Secrets are not cached by the Framework
    - Secrets appear as `[REDACTED]` in the Framework logs or any print statements
    - Secrets are retrieved only at pipeline execution time
    - Secrets appear as `[REDACTED]` in any downstream conversions

.. warning::

    DO NOT CHANGE THE SECRET MANAGER IMPLEMENTATION WITHOUT TALKING TO YOUR FRAMEWORK OWNER FIRST!

Configuration
------------

| **Scope: Pipeline**
| In a Pipeline bundle, secrets are defined in the following configuration file: ``src/pipeline_config/<deployment environment>_secrets.json|yaml``
| e.g. ``src/pipeline_config/dev_secrets.json|yaml``

Configuration Schema
--------------------
An secrets config file has the following structure:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "<secret alias_1>": {
                 "scope": "<secret scope>",
                 "key": "<secret key>"
             },
             "<secret alias_2>": {
                 "scope": "<secret scope>",
                 "key": "<secret key>"
             },
             ...
         }

   .. tab:: YAML

      .. code-block:: yaml

         <secret alias_1>:
           scope: <secret scope>
           key: <secret key>
         <secret alias_2>:
           scope: <secret scope>
           key: <secret key>
         ...

.. list-table::
   :header-rows: 1

   * - Field
     - Description
   * - **secret alias**
     - The alias used to reference the secret in your data flow specs
   * - **scope**
     - The Secret Scope that the secret belongs to in Databricks
   * - **key**
     - The key of the secret in the specified Secret Scope.

Referencing Secrets in Data Flow Specs
-------------------------------------
Secrets can be referenced as a value in any part of your data flow specs by using the folowing syntax: ``${secret.<secret_alias>}``.

For example, assume we want to connect to Kafka and we need to provide a keystore password. We would first ensure that the secret is configued in the secrets config file discussed above as follows:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "kafka_source_bootstrap_servers_password": {
                 "scope": "mySecretScope",
                 "key": "KafkaSecretKey"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         kafka_source_bootstrap_servers_password:
           scope: mySecretScope
           key: KafkaSecretKey

We can then reference the secret in any data flow spec as per the highligheted line in the code sample below:

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 12

         {
             "dataFlowId": "kafka_source_topic_1_staging",
             "dataFlowGroup": "kafka_samples",
             "dataFlowType": "standard",
             "sourceSystem": "testSystem",
             "sourceType": "kafka",
             "sourceViewName": "v_topic_1",
             "sourceDetails": {
                 "readerOptions": {
                     "kafka.bootstrap.servers": "{kafka_source_bootstrap_servers}",
                     "kafka.security.protocol": "SSL",
                     "kafka.ssl.keystore.password": "${secret.kafka_source_bootstrap_servers_password}",
                     "subscribe": "{kafka_source_topic}",
                     "startingOffsets": "earliest"
                 }
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "topic_1_staging",
                 "tableProperties": {
                     "delta.enableChangeDataFeed": "true"
                 }
             },
             "dataQualityExpectationsEnabled": false,
             "quarantineMode": "off"
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 11

         dataFlowId: kafka_source_topic_1_staging
         dataFlowGroup: kafka_samples
         dataFlowType: standard
         sourceSystem: testSystem
         sourceType: kafka
         sourceViewName: v_topic_1
         sourceDetails:
           readerOptions:
             kafka.bootstrap.servers: '{kafka_source_bootstrap_servers}'
             kafka.security.protocol: SSL
             kafka.ssl.keystore.password: ${secret.kafka_source_bootstrap_servers_password}
             subscribe: '{kafka_source_topic}'
             startingOffsets: earliest
         mode: stream
         targetFormat: delta
         targetDetails:
           table: topic_1_staging
           tableProperties:
             delta.enableChangeDataFeed: 'true'
         dataQualityExpectationsEnabled: false
         quarantineMode: 'off'

Best Practices
-------------
1. Never store secrets in code or configuration files
2. Use appropriate secret scopes for different environments
3. Rotate secrets regularly
4. Limit access to secret scopes

Troubleshooting
---------------

Secret Access Denied
^^^^^^^^^^^^^^^^^^^^
- Verify secret scope exists
- Check access permissions
- Validate key names
- Review scope configuration

Configuration Errors
^^^^^^^^^^^^^^^^^^^^
- Validate config file format
- Check for missing fields
- Verify string values
- Review scope/key names