Stream-Static - Streaming Data Warehouse
=========================================

Description
------------
Suitable for when you have a streaming table that you need to join to one or many additional static tables in order to derive your desired target data set, but you also want updates to the static tables to be reflected as they occur.

Use when:

- You want to join multiple streaming tables.
- You want changes in any/all tables to be updated as they occur.
- You only need to perform basic single row transforms.

**Layers:**

- Silver
- Gold (no complex transforms or aggregations)

**Models:**

- 3NF such as ODS, Inmon and Enterprise Models
- Data Vault
- Dimensional: dimensions and basic transactional facts

**Data Flow Components:**

.. image:: images/stream_static_dwh.png
   :target: _images/stream_static_dwh.png
   :alt: Stream Static - Streaming DWH

.. list-table::
   :header-rows: 1
   :widths: 5 15 60 20

   * - No.
     - Component
     - Description
     - M / O
   * - 1
     - Input Views
     - Input views are created over each streaming source table (as many as required). These views need only return:
       
       - the columns required for the necessary joins
       - a Sequence By column if this is an SCD 1/2 use case
       
       These views can optionally read from CDF if the source tables are CDF enabled.
     - M
   * - 2
     - Append Flows
     - Append flows load only the PK's and Sequnce By columns into a staging table.
     - M
   * - 3
     - Staging Append Only Table
     - A streaming append only table, the schema of which consists of only the primary keys and sequence by columns returned by each input view.
     - M
   * - 4
     - Change Flow
     - A single change flow loads the data into the staging merge table. It essentially merges and dedupes all the rows.
     - M
   * - 5
     - Staging Merge Table
     - A streaming table, the schema of which consists of only the primary keys and sequence by columns. CDF is enabled on this table.
     - M
   * - 6
     - Stream-static Join View
     - A view that implements the frameworks delta-join source type. It uses the previous staging table as the driving streaming table, reading from its CDF feed, and performs static joins to ALL the tables defined in the join.
     - M
   * - 7
     - Final Transform View
     - A view that applies a SQL transform (SELECT or CTE) to the data returned by the Stream-static Join View. This is optional and not required if no transformation needs to be applied. If you don't have a transform requirement you can omit the transform view. You may for example only need to specify which columns you want or perform a basic column renaming, which you can do in the Stream-static Join View (component 6).
     - O
   * - 8
     - Append or Change Flow
     - An Append Flow (for transactional or fact based target tables) or an SCD1/2 Change Flow that loads the data into the final target table.
     - M
   * - 9
     - Target Table
     - A streaming table, the schema of which is specified in the dataflowspec. This table is the final target table for the given flow.
     - M

Feature Support
----------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Supported
     - Not Supported
   * - - Append Only & SCD 1/2
       - Basic transforms such as:

         - Data type conversion
         - Concatenation
         - Single row calculations
         - Formatting

       - Cleansing & Data Quality Rules
       - Conditionals and calculations (single row) across multiple source tables
       - Joins
     - - Complex transforms such as aggregations
       - Window By

Considerations and Limitations
-------------------------------
- More complex to implement than the Stream-Static Basic pattern but allows for true streaming joins.

Sample
------
- Bundle: ``dlt_framework/src/samples/silver_sample``
- Sample: ``dlt_framework/src/samples/silver_sample/src/dataflows/stream_static_p7``

Example Data Flow
------------------

Day 1 Load
~~~~~~~~~~
- **Source Tables (Append-Only)**

    CUSTOMER

    .. list-table::
       :header-rows: 1
       :widths: 15 15 15 25 30

       * - customer_id
         - first_name
         - last_name
         - email
         - load_timestamp
       * - 1
         - John
         - Doe
         - john.doe@example.com
         - 2023-01-01 10:00
       * - 2
         - Jane
         - Smith
         - jane.smith@example.com
         - 2023-01-01 10:00

    CUSTOMER_ADDRESS

    .. list-table::
       :header-rows: 1
       :widths: 15 15 15 30

       * - customer_id
         - city
         - state
         - load_timestamp
       * - 1
         - Melbourne
         - VIC
         - 2023-01-01 10:00
       * - 2
         - Melbourne
         - VIC
         - 2023-01-01 10:00
       * - 4
         - Hobart
         - TAS
         - 2023-01-01 10:00

- **Staging Table (stg_source_1_appnd)**

    .. list-table::
       :header-rows: 1
       :widths: 30 70

       * - customer_id
         - load_timestamp
       * - 1
         - 2023-01-01 10:00
       * - 2
         - 2023-01-01 10:00
       * - 1
         - 2023-01-01 10:00
       * - 2
         - 2023-01-01 10:00
       * - 4
         - 2023-01-01 10:00

- **Target Table**
    
    - Append-Only Scenario

        .. list-table::
           :header-rows: 1
           :widths: 12 12 12 12 20 12 10 10

           * - customer_id
             - first_name
             - last_name
             - full_name
             - email
             - city
             - state
             - load_timestamp
           * - 1
             - John
             - Doe
             - John Doe
             - john.doe@example.com
             - Melbourne
             - VIC
             - 2023-01-01 10:00
           * - 2
             - Jane
             - Smith
             - Jane Smith
             - jane.smith@example.com
             - Melbourne
             - VIC
             - 2023-01-01 10:00

    - SCD1 Scenario

        .. list-table::
           :header-rows: 1
           :widths: 12 12 12 12 20 12 10

           * - customer_id
             - first_name
             - last_name
             - full_name
             - email
             - city
             - state
           * - 1
             - John
             - Doe
             - John Doe
             - john.doe@example.com
             - Melbourne
             - VIC
           * - 2
             - Jane
             - Smith
             - Jane Smith
             - jane.smith@example.com
             - Melbourne
             - VIC

    - SCD2 Scenario

        .. list-table::
           :header-rows: 1
           :widths: 12 12 12 12 20 12 10 15 15

           * - customer_id
             - first_name
             - last_name
             - full_name
             - email
             - city
             - state
             - _START_AT
             - _END_AT
           * - 1
             - John
             - Doe
             - John Doe
             - john.doe@example.com
             - Melbourne
             - VIC
             - 2023-01-01 10:00
             - NULL
           * - 2
             - Jane
             - Smith
             - Jane Smith
             - jane.smith@example.com
             - Melbourne
             - VIC
             - 2023-01-01 10:00
             - NULL

Day 2 Load
~~~~~~~~~~~
- **Source Tables (Append-Only)**

    CUSTOMER

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>email</th> <th>load_timestamp</th> </tr>
        <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>john.doe@example.com</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>jane.smith@example.com</td> <td>2023-01-01 10:00</td> </tr>
        <tr class="highlight-row"> <td>1</td> <td>John</td> <td>Doe</td> <td>jdoe@example.com</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>3</td> <td>Alice</td> <td>Green</td> <td>alice.green@example.com</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>joe.bloggs@example.com</td> <td>2023-01-02 10:00</td> </tr>
        </table>
    
    CUSTOMER_ADDRESS

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>city</th> <th>state</th> <th>load_timestamp</th> </tr>
        <tr> <td>1</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>4</td> <td>Hobart</td> <td>TAS</td> <td>2023-01-01 10:00</td> </tr>
        <tr class="highlight-row"> <td>2</td> <td>Perth</td> <td>WA</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>3</td> <td>Sydney</td> <td>NSW</td> <td>2023-01-02 10:00</td> </tr>
        </table>

- **Staging Table (stg_source_1_appnd)**

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>load_timestamp</th> </tr>
        <tr> <td>1</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>1</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>4</td> <td>2023-01-01 10:00</td> </tr>
        <tr class="highlight-row"> <td>1</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>3</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>2</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>3</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>4</td> <td>2023-01-02 10:00</td> </tr>
        </table>

- **Staging Table (stg_source_1_mrg)**

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>_START_AT</th> <th>_END_AT</th> </tr>
        <tr class="highlight-row"> <td>1</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
        <tr> <td>1</td> <td>2023-01-01 10:00</td> <td class="highlight-cell">2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>2</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
        <tr> <td>2</td> <td>2023-01-01 10:00</td> <td class="highlight-cell">2023-01-02 10:00</td> </tr>
        <tr> <td>3</td> <td>2023-01-01 10:00</td> <td>NULL</td> </tr>
        <tr class="highlight-row"> <td>4</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
        <tr> <td>4</td> <td>2023-01-01 10:00</td> <td class="highlight-cell">2023-01-02 10:00</td> </tr>
        </table>

- **Target Table**

    - Append-Only Scenario

        .. raw:: html

            <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>full_name</th> <th>email</th> <th>city</th> <th>state</th> <th>load_timestamp</th> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>john.doe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
            <tr class="highlight-row"> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>jdoe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-02 10:00</td> </tr>
            <tr class="highlight-row"> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Perth</td> <td>WA</td> <td>2023-01-02 10:00</td> </tr>        
            <tr class="highlight-row"> <td>3</td> <td>Alice</td> <td>Green</td> <td>alice.green@example.com</td> <td>alice.green@example.com</td> <td>Sydney</td> <td>NSW</td> <td>2023-01-02 10:00</td> </tr>
            <tr class="highlight-row"> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>Joe Bloggs</td> <td>joe.bloggs@example.com</td> <td>Hobart</td> <td>TAS</td> <td>2023-01-02 10:00</td> </tr>
            </table>  

    - SCD1 Scenario

        .. raw:: html

            <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>full_name</th> <th>email</th> <th>city</th> <th>state</th> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td class="highlight-cell">jdoe@example.com</td> <td>Melbourne</td> <td>VIC</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td class="highlight-cell">Perth</td> <td class="highlight-cell">WA</td> </tr>
            <tr class="highlight-row"> <td>3</td> <td>Alice</td> <td>Green</td> <td>alice.green@example.com</td> <td>alice.green@example.com</td> <td>Sydney</td> <td>NSW</td> </tr>
            <tr class="highlight-row"> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>Joe Bloggs</td> <td>joe.bloggs@example.com</td> <td>Hobart</td> <td>TAS</td> </tr>
            </table>

    - SCD2 Scenario

        .. raw:: html

            <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>full_name</th> <th>email</th> <th>city</th> <th>state</th> <th>_START_AT</th> <th>_END_AT</th> </tr>
            <tr class="highlight-row"> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>jdoe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>john.doe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> <td class="highlight-cell">2023-01-02 10:00</td> </tr>
            <tr class="highlight-row"> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Perth</td> <td>WA</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> <td class="highlight-cell">2023-01-02 10:00</td> </tr>
            <tr> <td>3</td> <td>Alice</td> <td>Green</td> <td>Alice Green</td> <td>alice.green@example.com</td> <td>Sydney</td> <td>NSW</td> <td>2023-01-01 10:00</td> <td>NULL</td> </tr>
            <tr class="highlight-row"> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>Joe Bloggs</td> <td>joe.bloggs@example.com</td> <td>Hobart</td> <td>TAS</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
            </table>

Day 3 Load
~~~~~~~~~~~
- **Source Tables (Append-Only)**

    CUSTOMER

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>email</th> <th>load_timestamp</th> </tr>
        <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>john.doe@example.com</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>jane.smith@example.com</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>jdoe@example.com</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>3</td> <td>Alice</td> <td>Green</td> <td>alice.green@example.com</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>joe.bloggs@example.com</td> <td>2023-01-02 10:00</td> </tr>
        </table>
    
    CUSTOMER_ADDRESS

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>city</th> <th>state</th> <th>load_timestamp</th> </tr>
        <tr> <td>1</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>4</td> <td>Hobart</td> <td>TAS</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>Perth</td> <td>WA</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>3</td> <td>Sydney</td> <td>NSW</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>1</td> <td>Brisbane</td> <td>QLD</td> <td>2023-01-03 10:00</td> </tr>
        </table>

- **Staging Table (stg_source_1_appnd)**

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>load_timestamp</th> </tr>
        <tr> <td>1</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>1</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>2</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>4</td> <td>2023-01-01 10:00</td> </tr>
        <tr> <td>1</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>3</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>2</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>3</td> <td>2023-01-02 10:00</td> </tr>
        <tr class="highlight-row"> <td>1</td> <td>2023-01-03 10:00</td> </tr>
        </table>

- **Staging Table (stg_source_1_mrg)**

    .. raw:: html

        <table class="docutils align-default"> <tr> <th>customer_id</th> <th>_START_AT</th> <th>_END_AT</th> </tr>
        <tr class="highlight-row"> <td>1</td> <td>2023-01-03 10:00</td> <td>NULL</td> </tr>
        <tr> <td>1</td> <td>2023-01-02 10:00</td> <td class="highlight-cell">2023-01-03 10:00</td> </tr>
        <tr> <td>1</td> <td>2023-01-01 10:00</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>2</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
        <tr> <td>2</td> <td>2023-01-01 10:00</td> <td>2023-01-02 10:00</td> </tr>
        <tr> <td>3</td> <td>2023-01-01 10:00</td> <td>NULL</td> </tr>
        <tr> <td>4</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
        <tr> <td>4</td> <td>2023-01-01 10:00</td> <td>2023-01-02 10:00</td> </tr>
        </table>

- **Target Table**

    - Append-Only Scenario

        .. raw:: html

            <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>full_name</th> <th>email</th> <th>city</th> <th>state</th> <th>load_timestamp</th> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>john.doe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>jdoe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-02 10:00</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Perth</td> <td>WA</td> <td>2023-01-02 10:00</td> </tr>        
            <tr> <td>3</td> <td>Alice</td> <td>Green</td> <td>alice.green@example.com</td> <td>alice.green@example.com</td> <td>Sydney</td> <td>NSW</td> <td>2023-01-02 10:00</td> </tr>
            <tr> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>Joe Bloggs</td> <td>joe.bloggs@example.com</td> <td>Hobart</td> <td>TAS</td> <td>2023-01-02 10:00</td> </tr>
            <tr class="highlight-row"> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>jdoe@example.com</td> <td>Brisbane</td> <td>QLD</td> <td>2023-01-02 10:00</td> </tr>
            </table>  

    - SCD1 Scenario

        .. raw:: html

            <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>full_name</th> <th>email</th> <th>city</th> <th>state</th> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>jdoe@example.com</td> <td class="highlight-cell">Brisbane</td> <td class="highlight-cell">QLD</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Perth</td> <td>WA</td> </tr>
            <tr> <td>3</td> <td>Alice</td> <td>Green</td> <td>alice.green@example.com</td> <td>alice.green@example.com</td> <td>Sydney</td> <td>NSW</td> </tr>
            <tr> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>Joe Bloggs</td> <td>joe.bloggs@example.com</td> <td>Hobart</td> <td>TAS</td> </tr>
            </table>

    - SCD2 Scenario

        .. raw:: html

            <table class="docutils align-default"> <tr> <th>customer_id</th> <th>first_name</th> <th>last_name</th> <th>full_name</th> <th>email</th> <th>city</th> <th>state</th> <th>_START_AT</th> <th>_END_AT</th> </tr>
            <tr class="highlight-row"> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>jdoe@example.com</td> <td>Brisbane</td> <td>QLD</td> <td>2023-01-03 10:00</td> <td>NULL</td> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>jdoe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-02 10:00</td> <td class="highlight-cell">2023-01-03 10:00</td> </tr>
            <tr> <td>1</td> <td>John</td> <td>Doe</td> <td>John Doe</td> <td>john.doe@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> <td>2023-01-03 10:00</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Perth</td> <td>WA</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
            <tr> <td>2</td> <td>Jane</td> <td>Smith</td> <td>Jane Smith</td> <td>jane.smith@example.com</td> <td>Melbourne</td> <td>VIC</td> <td>2023-01-01 10:00</td> <td>2023-01-02 10:00</td> </tr>
            <tr> <td>3</td> <td>Alice</td> <td>Green</td> <td>Alice Green</td> <td>alice.green@example.com</td> <td>Sydney</td> <td>NSW</td> <td>2023-01-01 10:00</td> <td>NULL</td> </tr>
            <tr> <td>4</td> <td>Joe</td> <td>Bloggs</td> <td>Joe Bloggs</td> <td>joe.bloggs@example.com</td> <td>Hobart</td> <td>TAS</td> <td>2023-01-02 10:00</td> <td>NULL</td> </tr>
            </table>