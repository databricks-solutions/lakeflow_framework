Change Data Feed (CDF)
======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta/delta-change-data-feed


Overview
--------
Change Data Feed (CDF) is a Delta Lake feature that enables tracking of row-level changes between versions of a Delta table. 
The framework provides built-in support for CDF to help track and process data changes efficiently.

Configuration
-------------

Enabling CDF on a Table
~~~~~~~~~~~~~~~~~~~~~~~

To enable CDF on a target table or staging table, you need to add the ``delta.enableChangeDataFeed`` property to the ``tableProperties`` object of the ``targetDetails`` object in your Data Flow Spec and set it to ``true``. For example:

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 6

         {
           "targetFormat": "delta",
           "targetDetails": {
               "table": "my_table",
               "tableProperties": {
                   "delta.enableChangeDataFeed": "true"
               },
               "schemaPath": "customer_schema.json"
           }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 5

         targetFormat: delta
         targetDetails:
           table: my_table
           tableProperties:
             delta.enableChangeDataFeed: 'true'
           schemaPath: customer_schema.json

Reading From CDF in a View
~~~~~~~~~~~~~~~~~~~~~~~~~~

To read from CDF, you need to do so via a view. When specifying a view in your Data Flow Spec, set the ``cdfEnabled`` attribute to ``true``. There are different types of dataflow specs and ways to specify a view, refer to the :doc:`dataflow_spec_reference` documentation for more information.

Standard Dataflow Spec example:

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 6

         {
           "sourceViewName": "v_customer_address",
           "sourceDetails": {
               "database": "{bronze_schema}",
               "table": "customer_address",
               "cdfEnabled": true
           }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 5

         sourceViewName: v_customer_address
         sourceDetails:
           database: '{bronze_schema}'
           table: customer_address
           cdfEnabled: true

Flows Dataflow Spec example:

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 9

         {
           "views": {
             "v_customer": {
               "mode": "stream",
               "sourceType": "delta",
               "sourceDetails": {
                 "database": "{bronze_schema}",
                 "table": "customer",
                 "cdfEnabled": true
               }
             }
           }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 8

         views:
           v_customer:
             mode: stream
             sourceType: delta
             sourceDetails:
               database: '{bronze_schema}'
               table: customer
               cdfEnabled: true

Important Considerations:
-------------------------

Refer to the Databricks `documentation <https://docs.databricks.com/aws/en/delta/delta-change-data-feed>`_ for information on:

* Concepts
* Schema / CDF columns
* Change types
* Limitations
