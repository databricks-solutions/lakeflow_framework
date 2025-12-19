Multi-Source Streaming and Flow Groups
######################################

The :doc:`Multi-Source Streaming <feature_multi_source_streaming>` feature allows you to stream multiple flows into a single target. 

Per the :doc:`Concepts <concepts>` section of this documentation, Flow Groups are used to logically group flows. This is useful when you have multiple complex sources and makes data flow development and maintenance more manageable.

You can design your pipelines with multiple flow groups, e.g if you have tables from 50 source systems streaming into one target table via a series of different transformations, you would likely design your data flow to have 50 Flow Groups, one for each source.

The diagram below shows a data flow with two flow groups, each with their own flows, and each populating the same target table:

.. image:: images/stream_multi_monolithic.png
   :target: _images/stream_multi_monolithic.png
   :alt: Monolithic Pipelines

.. important::

   Per the :ref:`concepts` section of this documentation, Flow Groups and Flows can be added and removed from a data flow as your requirements and systems evolve. This will not break the existing pipeline and will not require a full refresh of the Pipeline.