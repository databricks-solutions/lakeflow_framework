Data Flow Spec Reference
########################

Key concepts that you should familiarize yourself with before reading this section are explained in the section: :ref:`concepts_data_flows`.

A Data Flow Spec is a JSON file that defines the structure of a single data flow that is ultimately executed by a Spark Declarative Pipeline. 

.. important:: 
   
   * A Data Flow Spec must adhere to the schemas defined by the framework, which is documented in this section.
   * In general a single Data Flow Spec will be contained in one file and must be named with the suffix ``_main.json`` to be picked up by the framework.
   * In the case of Flows Data Flow Specs, the Data Flow Spec can also be broken up into a main and one or more flow files. The main spec file will contain the main pipeline configuration and the flow spec file will contain the flow groups. This is explained further in the section: :doc:`/build/spec-reference/splitting-dataflow-spec`.

.. toctree::
   :maxdepth: 1
   
   standard
   flows
   materialized-views