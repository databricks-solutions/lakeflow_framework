Substitutions
=============

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Framework Bundle` :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Global` :bdg-success:`Pipeline`
   * - **Databricks Docs:**
     - NA

When deploying pipeline bundles to different environments (dev, sit, prod), there will normally be a need to cater for differences in resource names (e.g. schema names, storage accounts, url's ) across environments. The substitutions feature caters for this by allowing you to substitute values in your Data Flow Spec and SQL scripts, with values defined in a configuration file.

Substitutions can be configured in two ways:

* **tokenized** 
   Tokens can be included in your Data Flow Spec's or SQL statements, indicated by curly braces and a substitution value can be assigned to them in the substitution config file. 
   Note, tokens can be applied recursively.
* **prefix/suffix**
   Prefixes and suffixes can be assigned to dataflow_spec attributes. This will automatically add the prefix or suffix to value of the attribute in every spot where that attribute is present in a Data Flow Spec even if it is nested.

There are a few reserved tokens that exist by default. Below is a list of the reserved tokens.
    
    * *workspace_env*: The target workspace environment, this is the one that appears in the ``databricks.yml`` file

.. important::

    Ensure that commonly used substitutions are stored in the Global Framework configuration rather than individual Pipeline Bundles.
    
    For example, maintain schema names in global substitution files.

Configuration
-------------

| **Scope: Global**
| In the Framework bundle, substitutions are defined in the following configuration file: ``src/config/<deployment environment/target>_substitutions.json|yaml``
| e.g. ``src/config/dev_substitutions.json|yaml``

| **Scope: Pipeline**
| In a Pipeline bundle, substitutions are defined in the following configuration file: ``src/pipeline_configs/<deployment environment/target>_substitutions.json|yaml``
| e.g. ``src/pipeline_configs/dev_substitutions.json|yaml``

.. note::

    The ``<deployment environment/target>`` portion of the substitutions config file name must be the same as one of the environment targets listed in the ``databricks.yml`` file, as this determines which environment the bundle will be deployed to. 

.. admonition:: Precedence
   :class: note
    
    The Global substitutions and Pipeline substitutions are merged, with Pipeline substitutions taking precedence.

Configuration Schema
--------------------

The structure of the substitutions config file should be as below:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "tokens": {
                 "<token>": "<value>",
                 ...
             },
             "prefix_suffix": {
                 "<attrbute_name>": {
                     "prefix | suffix": "<value>"
                 },
                 ...
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         tokens:
           <token>: <value>
           ...
         prefix_suffix:
           <attrbute_name>:
             prefix | suffix: <value>
           ...

.. list-table::
   :header-rows: 1

   * - Field
     - Description
   * - **tokens**
     - key-value pairs for tokenized substitutions.
   * - **prefix_suffix**
     - Object that containing a additional objects defining the substitution behavior for the given attributes.

        * attribute_name: the Data Flow Spec attribute you wish to apply the prefix or suffix to.
        * prefix | suffix: the substitution mode.
        * value: the value to be added as a prefix or suffix. NOTE: 
            * the value can be a token.
            * workspace_env is a reserved token that can be used to pass through the workspace environment (from the ``databricks.yml`` file).

Examples
--------
Below is a sample output of substitutions applied for a given substitutions file and Data Flow Spec. 

Substitutions config:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "tokens": {
                 "bronze_schema_x": "bronze_marketing",
                 "bronze_schema_y": "bronze_collections"
             },
             "prefix_suffix": {
                 "database": {
                     "suffix": "{workspace_env}"
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         tokens:
           bronze_schema_x: bronze_marketing
           bronze_schema_y: bronze_collections
         prefix_suffix:
           database:
             suffix: '{workspace_env}'

Data Flow Spec input:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             ...
                 "flows": {
                     "f_contract": {
                         "flowType": "append_view",
                         "flowDetails": {
                             "targetTable": "staging_table_apnd_3",
                             "sourceView": "v_brz_contract"
                         },
                         "views": {
                             "v_brz_contract": {
                                 "mode": "stream",
                                 "sourceType": "delta",
                                 "sourceDetails": {
                                     "database": "main.{bronze_schema_x}",
                                     "table": "contract",
                                     "cdfEnabled": true,
                                     "selectExp": [
                                         "*"
                                     ],
                                     "whereClause": []
                                 }
                             }
                         }
                     },
                     "f_loan": {
                         "flowType": "append_view",
                         "flowDetails": {
                             "targetTable": "staging_table_apnd_3",
                             "sourceView": "v_brz_loan"
                         },
                         "views": {
                             "v_brz_loan": {
                                 "mode": "stream",
                                 "sourceType": "delta",
                                 "sourceDetails": {
                                     "database": "main.{bronze_schema_y}",
                                     "table": "loan",
                                     "cdfEnabled": true,
                                 }
                             }
                         }
                     },
                     ...
                 }
             ...
         }

   .. tab:: YAML

      .. code-block:: yaml

         ...
         flows:
           f_contract:
             flowType: append_view
             flowDetails:
               targetTable: staging_table_apnd_3
               sourceView: v_brz_contract
             views:
               v_brz_contract:
                 mode: stream
                 sourceType: delta
                 sourceDetails:
                   database: main.{bronze_schema_x}
                   table: contract
                   cdfEnabled: true
                   selectExp:
                   - '*'
                   whereClause: []
           f_loan:
             flowType: append_view
             flowDetails:
               targetTable: staging_table_apnd_3
               sourceView: v_brz_loan
             views:
               v_brz_loan:
                 mode: stream
                 sourceType: delta
                 sourceDetails:
                   database: main.{bronze_schema_y}
                   table: loan
                   cdfEnabled: true
           ...
         ...

Data Flow Spec output:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             ...
                 "flows": {
                     "f_contract": {
                         "flowType": "append_view",
                         "flowDetails": {
                             "targetTable": "staging_table_apnd_3",
                             "sourceView": "v_brz_contract"
                         },
                         "views": {
                             "v_brz_contract": {
                                 "mode": "stream",
                                 "sourceType": "delta",
                                 "sourceDetails": {
                                     "database": "main.bronze_marketing_dev",
                                     "table": "contract",
                                     "cdfEnabled": true,
                                     "selectExp": [
                                         "*"
                                     ],
                                     "whereClause": []
                                 }
                             }
                         }
                     },
                     "f_loan": {
                         "flowType": "append_view",
                         "flowDetails": {
                             "targetTable": "staging_table_apnd_3",
                             "sourceView": "v_brz_loan"
                         },
                         "views": {
                             "v_brz_loan": {
                                 "mode": "stream",
                                 "sourceType": "delta",
                                 "sourceDetails": {
                                     "database": "main.bronze_collections_dev",
                                     "table": "loan",
                                     "cdfEnabled": true,
                                 }
                             }
                         }
                     },
                     ...
                 }
             ...
         }

   .. tab:: YAML

      .. code-block:: yaml

         ...
         flows:
           f_contract:
             flowType: append_view
             flowDetails:
               targetTable: staging_table_apnd_3
               sourceView: v_brz_contract
             views:
               v_brz_contract:
                 mode: stream
                 sourceType: delta
                 sourceDetails:
                   database: main.bronze_marketing_dev
                   table: contract
                   cdfEnabled: true
                   selectExp:
                   - '*'
                   whereClause: []
           f_loan:
             flowType: append_view
             flowDetails:
               targetTable: staging_table_apnd_3
               sourceView: v_brz_loan
             views:
               v_brz_loan:
                 mode: stream
                 sourceType: delta
                 sourceDetails:
                   database: main.bronze_collections_dev
                   table: loan
                   cdfEnabled: true
           ...
         ...


You will notice the database fields all have the workspace environment suffix added to it. 

The tokenized substitution takes place first then we can see there is a suffix of ``dev`` that is added to all fields that have the name database anywhere within the Data Flow Spec