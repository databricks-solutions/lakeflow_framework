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

1. If a new feature is added or change to existing feature, ensure the feature is well documented in a new feature file or update the existing feature file with the name ``feature_<feature_name>.rst``. Add it to the matching Features hub section and to the :doc:`features_a_z` index.

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

The documentation build dependencies are pinned in ``requirements-docs.lock``,
a hashed lockfile generated from ``requirements-docs.txt``. Installing from the
lockfile (rather than the unpinned ``requirements-docs.txt``) guarantees a
reproducible build and lets ``pip`` verify each package against its expected
hash.

To install the documentation dependencies, run the following command from the
root directory of the repository:

.. code-block:: bash

   pip install --require-hashes --no-deps -r requirements-docs.lock

.. note::

   ``--require-hashes`` makes ``pip`` verify the SHA-256 hash of every
   downloaded wheel/sdist against the hash recorded in the lockfile.
   ``--no-deps`` is safe (and recommended) here because the lockfile already
   contains the complete, fully-resolved transitive dependency set.

If you have already installed the full dev dependencies via
``requirements-dev.lock`` (see :doc:`contributor_dev_env`), you do **not** need
to install the documentation dependencies separately —
``requirements-dev.lock`` already includes everything in
``requirements-docs.lock``.

Updating dependencies / regenerating the lockfile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you add, remove, or bump a documentation dependency, edit
``requirements-docs.txt`` (the unhashed source-of-truth file) and then
regenerate the lockfile by running the helper script from the root of the
repository:

.. code-block:: bash

   ./scripts/generate_lockfiles.sh

This script regenerates ``requirements.lock``, ``requirements-dev.lock``, and
``requirements-docs.lock`` from their corresponding ``.txt`` files using
``pip-compile`` (from the ``pip-tools`` package, which you can install with
``pip install pip-tools``). Commit the regenerated ``.lock`` files alongside
your change to ``requirements-docs.txt`` in the same pull request so that CI
and other contributors stay in sync.

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
