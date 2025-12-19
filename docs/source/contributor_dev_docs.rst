Updating the Documentation
##########################

The documentation is written in `reStructuredText <http://docutils.sourceforge.net/rst.html>`_ format and is built using `Sphinx <http://sphinx-doc.org/>`_.

Sphinx was chosen for it's ease of use and ability to:

* easily generate a navigation bar and index.
* easily add cross references to other parts of the documentation.
* support for the more advanced documentation requirements for some of the pipeline pattern and feature documentation.

Source Files
------------

The source files for the documentation are located in the ``docs/source`` directory.

Writing Documentation
--------------------------

1. If a new feature is added or change to existing feature, ensure the feature is well documented in a new feature file or update the existing feature file with the name feature_<feature_name>.rst and add it to the :doc:`features` page.
   - In the feature file, include:
     - Feature description
     - Configuration options
     - Usage examples / sample code
2. Update Data Flow Spec reference where applicable


Styling
--------
Styling for the documentation which controls the look of the html output is in two main locations

1. The theme and options that are used to generate the html output is defined in the conf.py file. The existing theme should not be changed unless there is an agreement on a new theme.
   
   - More information on theming can be found here: https://www.sphinx-doc.org/en/master/usage/theming.html
   - The available html output options can be found here: https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
2. Custom styling can be found in the custom.css file which can be found in the docs/_static directory.
   
   - More information on how to add custom CSS can be found here: https://docs.readthedocs.com/platform/stable/guides/adding-custom-css.html#overriding-or-replacing-a-theme-s-stylesheet

Generating the Documentation
----------------------------

Supported Formats
~~~~~~~~~~~~~~~~~

Sphinx has been configured to generate the following formats:

* HTML
* Markdown

Dependencies
~~~~~~~~~~~~

To install the dependencies, ensure that the following command dev step up is executed and if not run the following command in the root directory of the repository:

.. code-block:: bash

   pip install -r requirements-dev.txt

Building the Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The Framework comes with a make file to build the documentation. There is one for Bash and one for Windows.

To build the documentation, run the following command in the docs directory:

* HTML:

   .. code-block:: bash

      make html

* Markdown:

   .. code-block:: bash

      make md

The above commands will build the documentation and save it in the ``docs/build`` directory.

To view the documentation, open the below files in your browser.:

* HTML: ``docs/build/html/index.html``
* Markdown: ``docs/build/markdown/index.md``

Clean the Documentation
~~~~~~~~~~~~~~~~~~~~~~~

Sometimes it will be necessary to delete the build directory and re-build the documentation. To do this, run the following command in the docs directory:

.. code-block:: bash

   make clean
