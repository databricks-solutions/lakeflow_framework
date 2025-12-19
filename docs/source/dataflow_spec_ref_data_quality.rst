Data Quality and Quarantine Configuration
-------------------------------------------

These properties control how data quality issues are handled:

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - **Field**
     - **Type**
     - **Description**
   * - **dataQualityExpectationsEnabled** (*optional*)
     - ``boolean``
     - A flag indicating whether data quality expectations are enabled (see :doc:`feature_data_quality_quarantine`).
   * - **dataQualityExpectationsPath** (*optional*)
     - ``string``
     - Either a relative path or filename for the expectations file. Note that the framework automatically calculates all relative paths from the appropriate expectations sub-folder, in the Pipeline Bundle. Examples:

       * All expectations files in the ``expectations`` sub-folder: ``.`` or ``*``
       * A specific expectations file: ``my_table_dqe.json``

   * - **quarantineMode** (*optional*)
     - ``string``
     - The mode for handling quarantined data. It can be `off`, `flag`, or `table`.  
       Supported: `["off", "flag", "table"]`
   * - **quarantineTargetDetails** (*optional*)
     - ``object``
     - Details about the quarantine target, only required if ``quarantineMode`` is set to ``table``.  
       See :ref:`quarantine-target-details` section below.

.. _quarantine-target-details:

quarantineTargetDetails
~~~~~~~~~~~~~~~~~~~~~~~

The `quarantineTargetDetails` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Type
     - Description
   * - targetFormat
     - ``string``
     - The format of the quarantine target. Currently, only ``delta`` is supported.
       
       | Supported: ``["delta"]``
       | Default: ``"delta"``
   * - table
     - ``string``
     - (*conditional*) The table name, required if ``targetFormat`` is ``delta``.
   * - tableProperties
     - ``object``
     - (*conditional*) Additional properties for the table, required if ``targetFormat`` is ``delta``.
   * - path 
     - ``string``
     - (*conditional*) The path to the table, required if ``targetFormat`` is ``delta``.