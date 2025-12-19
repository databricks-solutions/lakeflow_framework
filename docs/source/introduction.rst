Introduction to the Lakeflow Framework
##################################

The Lakeflow Framework is a meta-data driven, data engineering framework, designed to:

* accelerate and simplify the deployment of Spark Declarative Pipelines (SDP), and support their deployment through your SDLC.
* support a wide variety of patterns across the medallion architecture for both batch and streaming workloads.
* provide a structured, configuration-driven approach to building reliable and maintainable data pipelines

The Framework is designed for simplicity, performance, ease of maintenance and extensibility as the SDP product evolves. 

Core Concepts
-------------

* **Lego block, pattern-based development**
* **Two Parts**

  * SDP wrapper components: close to the metal, exposes SDP API’s directly to minimise the need for changes.
  * Dataflow Spec abstraction layer: allows users to put the SDP components together, as they needed, like Lego blocks.

* **Key Design**

  * DABS native
  * No artifacts or wheel files
  * Minimized third-party dependencies
  * No control tables
  * Extensible
  * Flexible deployment bundles

* **OO & Best Practices**

  * Encapsulation
  * Abstraction & Inheritance
  * Loosely Coupled
  * Separation of Concerns & Single Responsibility

Please refer to the :doc:`concepts` section for an overview of the different components of the framework.
