:orphan:

Multi-Source Streaming and Flow Groups
######################################

The :doc:`Multi-Source Streaming </features/platform/multi-source-streaming>` feature allows you to stream multiple flows into a single target. 

Per the :doc:`Architecture </architecture/index>` section of this documentation, Flow Groups are used to logically group flows. This is useful when you have multiple complex sources and makes data flow development and maintenance more manageable.

You can design your pipelines with multiple flow groups, e.g if you have tables from 50 source systems streaming into one target table via a series of different transformations, you would likely design your data flow to have 50 Flow Groups, one for each source.

The diagram below shows a data flow with two flow groups, each with their own flows, and each populating the same target table:

.. md-mermaid::

   flowchart TB
     subgraph pipeline ["SDP Pipeline — one or more target tables"]
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

.. important::

   Per the :doc:`/architecture/index` section of this documentation, Flow Groups and Flows can be added and removed from a data flow as your requirements and systems evolve. This will not break the existing pipeline and will not require a full refresh of the Pipeline.