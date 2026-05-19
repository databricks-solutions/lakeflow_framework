Development Environment Setup
#############################

The sections below assumes the Lakeflow Framework repository has been cloned from git and you are in the root directory. If not please do so first.

Setting up for development as a contributor to the Lakeflow Framework
=====================================================================

Once you have cloned the Lakeflow Framework repository, you'll need to follow the steps below to set up the framework.

1. **Install requirements**

   The dev dependencies are pinned and hash-verified in
   ``requirements-dev.lock`` (generated from ``requirements-dev.txt``).
   Installing from the lockfile guarantees a reproducible environment that
   matches what CI uses.

   Install them from the root directory by running the following command (you
   may also want to use a virtual environment for this by running
   ``python -m venv .venv/`` first. See `Python Virtual Environments
   <https://docs.python.org/3/tutorial/venv.html>`_ for more details):

   .. code-block:: bash

      pip install --require-hashes --no-deps -r requirements-dev.lock

   ``requirements-dev.lock`` includes everything in ``requirements-docs.lock``
   too, so you do not need a separate install step for building the
   documentation.

   If you change a dependency in any of the ``requirements*.txt`` files,
   regenerate all three lockfiles with the helper script from the repo root:

   .. code-block:: bash

      ./scripts/generate_lockfiles.sh

   See :doc:`contributor_dev_docs` for more details on the lockfiles.
2. **Set up VS Code extentions**
   
   Once you open the Lakeflow Framework workspace in VS Code for the first time, VS Code will prompt you to install the recommended extensions. 
   If you missed this prompt, you can review and install the recommended extensions with the Extensions: Show Recommended Extensions command or by clicking on the extentions tab on left side of the window and selecting "Workspace Recommendations".

.. note::

    To deploy the Lakeflow Framework to your Databricks workspace, follow the steps in :doc:`deploy_framework`.
