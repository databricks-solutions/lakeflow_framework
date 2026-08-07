Legacy Data Flow Spec Types
###########################

.. note::

   These are the **legacy** Data Flow Spec formats. New data flows should use
   the node-based spec documented in :doc:`/build/spec-reference/index`, which
   supersedes all three types below. The legacy formats remain fully supported.

A Data Flow Spec is a file that defines the structure of a single data flow that is ultimately executed by a Spark Declarative Pipeline.

.. important::

   * A Data Flow Spec must adhere to the schemas defined by the framework, which is documented in this section.
   * In general a single Data Flow Spec will be contained in one file and must be named with the suffix ``_main.json`` to be picked up by the framework.
   * In the case of Flows Data Flow Specs, the Data Flow Spec can also be broken up into a main and one or more flow files. The main spec file will contain the main pipeline configuration and the flow spec file will contain the flow groups. This is explained further in the section: :doc:`/build/spec-reference/splitting-dataflow-spec`.

The framework supports three legacy spec types:

.. toctree::
   :maxdepth: 1

   standard
   flows
   materialized-views
