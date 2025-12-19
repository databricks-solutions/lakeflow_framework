Data Quality - Expectations
============

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta-live-tables/expectations.html

Define expectations in your Data Flow Spec to apply quality constraints that validate data as it flows through ETL pipelines. 

Configuration
-------------

Defining Expectations
~~~~~~~~~~~~~~~~~~~~~
In a Pipeline Bundle bundle, expectations are defined at a table level and must be located in an ``expectations`` sub-folder of the directory containing the corresponding Data Flow Spec. Examples: 

* flat structure: ``src/dataflows/expectations/<table_name>_dqe.json`` 
* organized by target table: ``src/dataflows/<table>/expectations/<table_name>_dqe.json`` 

.. note::

    The expectations file name can have any name (with a .json extension), but best practice is to use the pattern ``<table_name>_dqe.json``.

The schema for the expectations file is defined below, in the :ref:`expectations-schema` section.

Enabling and Referencing Expectations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Once the expectations are defined, they can be enabled and referenced in the Data Flow Spec, per the following sections of this documentation:

* :ref:`Flows Data Flow - Data Quality Configuration <dataflow-spec-flows-data-quality-configuration>`
* :ref:`Standard Data Flow - Data Quality Configuration <dataflow-spec-standard-data-quality-configuration>`


.. _expectations-schema:

Expectations Schema
--------------------

.. code-block:: json

    {
        "<expectation_type>": [
            {
                "name": "<expectation name>",
                "contraint": "SQL constraint",
                "tag": "<tag>",
                "enabled": "<true or false>"
            }
        ]
    }

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - **type of expectation**
     - ``string``
     - The type of expectation. Valid types are:

        1. **expect**: Use the expect operator when you want to keep records that violate the expectation. Records that violate the expectation are added to the target dataset along with valid records
        2. **expect_or_drop** : Use the expect_or_drop operator when you want to drop records that violate the expectation. Records that violate the expectation are dropped from the target dataset
        3. **expect_or_fail**: Use the expect_or_fail operator when you want to fail the dataflow if any records violate the expectation. The dataflow will fail and stop execution if any records violate the expectation

   * - **name**
     - ``string``
     - The name of the expectation, any unique name can be given.
   * - **constraint**
     - ``string``
     - The SQL constraint that defines the expectation. The constraint should be a valid SQL query that returns a boolean value. If the constraint returns `true`, the record is considered valid; else, it is considered invalid.
   * - **tag** (*optional*)
     - ``string``
     - The tag is used to group expectations together.
   * - **enabled** (*optional*)
     - ``boolean``
     - Specifies if the expectation is enabled or not. If the expectation is enabled, it will be validated; otherwise, it will be ignored. If not specified, the expectation will be enabled by default.

Examples
--------

.. code-block:: json

    {
        "expect": [
            {
                "name": "expectation_1",
                "constraint": "column_1 > 0",
                "tag": "tag_1",
                "enabled": true
            }
        ],
        "expect_or_drop": [
            {
                "name": "expectation_2",
                "constraint": "column_2 < 100",
                "tag": "tag_2",
                "enabled": true
            }
        ],
        "expect_or_fail": [
            {
                "name": "expectation_3",
                "constraint": "column_3 != 'NULL'",
                "tag": "tag_3",
                "enabled": true
            }
        ]
    }
