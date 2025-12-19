Mandatory Table Properties
=========================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Framework Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Global`
   * - **Databricks Docs:**
     - https://docs.databricks.com/aws/en/delta/table-properties

The Mandatory Table Properties feature allows you to define a set of table properties that will be automatically applied to all tables created by the Framework. This ensures consistent table configurations across your data lakehouse.

Configuration
-------------

| **Scope: Global**
| Mandatory table properties are defined in the global configuration file located at ``src/config/global.json|yaml`` under the ``mandatory_table_properties`` section.

Configuration Schema
------------------

The mandatory table properties configuration are defined as key-value pairs as follows:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "mandatory_table_properties": {
                 "<property_name>": "<property_value>",
                 ...
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         mandatory_table_properties:
           <property_name>: <property_value>
           ...

Common Properties
---------------

Some commonly used table properties include:

.. list-table::
   :header-rows: 1

   * - Property
     - Description
     - Example Value
   * - **delta.autoOptimize.optimizeWrite**
     - Enables write optimization for the table
     - ``true``
   * - **delta.autoOptimize.autoCompact**
     - Enables automatic file compaction
     - ``true``
   * - **delta.enableChangeDataFeed**
     - Enables Change Data Feed for the table
     - ``true``
   * - **delta.columnMapping.mode**
     - Specifies the column mapping mode
     - ``"name"``
   * - **comment**
     - Adds a description to the table
     - ``"This table contains..."``

Example Configuration
-------------------

Here's an example configuration that sets some common table properties:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "mandatory_table_properties": {
                 "delta.autoOptimize.optimizeWrite": "true",
                 "delta.autoOptimize.autoCompact": "true",
                 "delta.enableChangeDataFeed": "true",
                 "delta.columnMapping.mode": "name"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         mandatory_table_properties:
           delta.autoOptimize.optimizeWrite: 'true'
           delta.autoOptimize.autoCompact: 'true'
           delta.enableChangeDataFeed: 'true'
           delta.columnMapping.mode: name

.. admonition:: Note
   :class: note
    
    - All property values must be specified as strings, even for boolean values
    - Properties defined here will be applied to all tables created by the Framework
    - These properties cannot be overridden at the individual table level

.. admonition:: Best Practice
   :class: note
    
    It's recommended to:
    
    - Enable auto-optimize features for better performance
    - Enable Change Data Feed if you need to track changes
    - Use column mapping to ensure schema evolution compatibility
    - Add meaningful table comments for documentation 