Scaling and Decomposing Pipelines
#################################

.. _patterns_scaling_pipelines:

There is no single rule for how to divide pipelines. Choices depend on organizational structure, CI/CD practices, data complexity (sources, transforms, volumes), latency and SLAs, and related constraints.

.. warning::

   Be aware of current Pipeline and concurrency limits for Spark Declarative Pipelines. Limits change over time; check:

   * https://docs.databricks.com/en/resources/limits.html
   * https://docs.databricks.com/en/delta-live-tables/limitations.html

Once you have chosen a logical grouping (see :doc:`/build/bundle-structure`), you can decompose a large pipeline where natural boundaries exist.

Example: start with one pipeline that has two Flow Groups flowing into a target via staging tables:

.. md-mermaid::

   flowchart TB
     subgraph pipeline ["SDP Pipeline — single pipeline, one or more target tables"]
       subgraph fg1 ["Flow Group 1"]
         direction LR
         IV1a["Input View:<br/>vw_source_table_1"]
         IV1b["Input View:<br/>vw_source_table_n+1"]
         STG1a["Streaming Table:<br/>stg_source1_apnd<br/>(Append Only)"]
         STG1b["Streaming Table:<br/>stg_source1_mrg<br/>(SCD2 + CDF Enabled)"]
         V1a["View:<br/>vw_source1_final_cdf"]
         V1b["View:<br/>vw_source1_final_tfm<br/>(SQL Transform)"]
         IV1a -->|append_flow| STG1a
         IV1b -->|append_flow| STG1a
         STG1a -->|"AUTO CDC flow:<br/>create_auto_cdc_flow()"| STG1b
         STG1b -->|"readStream()<br/>CDF enabled"| V1a
         V1a -->|spark.sql| V1b
       end
       subgraph fgn ["Flow Group n"]
         direction LR
         IVna["Input View:<br/>vw_source_table_1"]
         IVnb["Input View:<br/>vw_source_table_n+1"]
         STGna["Streaming Table:<br/>stg_sourceN_apnd<br/>(Append Only)"]
         STGnb["Streaming Table:<br/>stg_sourceN_mrg<br/>(SCD2)"]
         Vna["View:<br/>vw_sourceN_final_cdf"]
         Vnb["View:<br/>vw_sourceN_final_tfm<br/>(SQL Transform)"]
         IVna -->|append_flow| STGna
         IVnb -->|append_flow| STGna
         STGna -->|"AUTO CDC flow:<br/>create_auto_cdc_flow()"| STGnb
         STGnb -->|"readStream()<br/>CDF enabled"| Vna
         Vna -->|spark.sql| Vnb
       end
       TT["Streaming Table:<br/>TargetTable"]
       V1b -->|"Append or auto CDC Flow:<br/>append_flow() or create_auto_cdc_flow()"| TT
       Vnb -->|"Append or auto CDC Flow:<br/>append_flow() or create_auto_cdc_flow()"| TT
     end

The same design decomposed into three pipelines:

* Each Flow Group is its own pipeline, targeting a final staging table.
* A final pipeline merges upstream staging tables into the target table.

.. md-mermaid::

   flowchart TB
     subgraph sp1 ["SDP Staging Pipeline (Flow Group) 1"]
       direction LR
       IV1a["Input View:<br/>vw_source_table_1"]
       IV1b["Input View:<br/>vw_source_table_n+1"]
       STG1a["Streaming Table:<br/>stg_source1_apnd<br/>(Append Only)"]
       STG1b["Streaming Table:<br/>stg_source1_mrg<br/>(SCD2 + CDF Enabled)"]
       IV1a -->|append_flow| STG1a
       IV1b -->|append_flow| STG1a
       STG1a -->|"AUTO CDC flow:<br/>create_auto_cdc_flow()"| STG1b
     end
     subgraph spn ["SDP Staging Pipeline (Flow Group) N"]
       direction LR
       IVna["Input View:<br/>vw_source_table_1"]
       IVnb["Input View:<br/>vw_source_table_n+1"]
       STGna["Streaming Table:<br/>stg_sourceN_apnd<br/>(Append Only)"]
       STGnb["Streaming Table:<br/>stg_sourceN_mrg<br/>(SCD2)"]
       IVna -->|append_flow| STGna
       IVnb -->|append_flow| STGna
       STGna -->|"AUTO CDC flow:<br/>create_auto_cdc_flow()"| STGnb
     end
     subgraph fp ["SDP Final Pipeline"]
       direction TB
       V1a["View:<br/>vw_source1_final_cdf"]
       V1b["View:<br/>vw_source1_final_tfm<br/>(SQL Transform)"]
       Vna["View:<br/>vw_sourceN_final_cdf"]
       Vnb["View:<br/>vw_sourceN_final_tfm<br/>(SQL Transform)"]
       TT["Streaming Table:<br/>TargetTable"]
       V1a -->|spark.sql| V1b
       Vna -->|spark.sql| Vnb
       V1b -->|"Append or auto CDC Flow:<br/>append_flow() or create_auto_cdc_flow()"| TT
       Vnb -->|"Append or auto CDC Flow:<br/>append_flow() or create_auto_cdc_flow()"| TT
     end
     STG1b -->|"readStream()<br/>CDF enabled"| V1a
     STGnb -->|"readStream()<br/>CDF enabled"| Vna

For decomposed multi-source samples, see ``samples/pattern-samples`` (Multi Source Streaming Decomposed Staging and Final pipelines).

See also :doc:`/build/patterns/index` for the pattern catalog and :doc:`/build/patterns/mix-and-match-patterns`.
