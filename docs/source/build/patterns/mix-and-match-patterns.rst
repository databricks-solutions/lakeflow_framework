Mix and Match Patterns
####################

.. _patterns_mix_and_match:

A pipeline can include one or more data flows, each based on a different pattern. Within a single data flow you can also mix patterns across :ref:`Flow Groups <concepts_flows_data_flow>` that populate the same target table:

.. md-mermaid::

   flowchart LR
     subgraph pipeline ["SDP Pipeline — single pipeline, one or more target tables"]
       FG1["Flow Group 1<br/>Multi-Source Streaming"]
       FG2["Flow Group 2<br/>Stream-Static Complex"]
       FGN["Flow Group N<br/>…"]
       TT["Streaming Table:<br/>TargetTable"]
       FG1 -->|"Append or auto CDC Flow:<br/>append_flow() or create_auto_cdc_flow()"| TT
       FG2 -->|"Append or auto CDC Flow:<br/>append_flow() or create_auto_cdc_flow()"| TT
       FGN -->|"Append or auto CDC Flow:<br/>append_flow() or create_auto_cdc_flow()"| TT
     end

Flow Groups logically group flows (for example one group per source system). See :doc:`/architecture/index` and :doc:`/features/platform/multi-source-streaming`. Groups and flows can be added or removed over time without a full pipeline refresh.

See also :doc:`/build/patterns/index` for the pattern catalog and :doc:`/build/patterns/scaling-decomposing-pipelines`.
