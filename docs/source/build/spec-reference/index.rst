Data Flow Spec Reference
########################

Key concepts that you should familiarize yourself with before reading this section are explained in the section: :ref:`concepts_data_flows`.

A Data Flow Spec is a file that defines the structure of a single data flow that is ultimately executed by a Spark Declarative Pipeline.

.. important::

   * A Data Flow Spec must adhere to the schemas defined by the framework, which is documented in this section.
   * In general a single Data Flow Spec will be contained in one file and must be named with the suffix ``_main.json`` to be picked up by the framework.

.. toctree::
   :maxdepth: 1

   nodespec
   legacy
