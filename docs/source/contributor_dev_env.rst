Development Environment Setup
#############################

The sections below assumes the Lakeflow Framework repository has been cloned from git and you are in the root directory. If not please do so first.

Setting up for development as a contributor to the Lakeflow Framework
================================================================

Once you have cloned the Lakeflow Framework repository, you'll need to follow the steps below to set up the framework.

1. **Install requirements**
   
   Install the required dev dependencies from the root directory by running the following command (you may also want to use a virtual environment, venv for this by running ``python -m venv .venv/`` before running the command below to install dev requirements. See more `Python Virtual Environments <https://docs.python.org/3/tutorial/venv.html>`_): 
   ```bash
   pip install -r requirements-dev.txt
   ```
2. **Set up VS Code extentions**
   
   Once you open the Lakeflow Framework workspace in VS Code for the first time, VS Code will prompt you to install the recommended extensions. 
   If you missed this prompt, you can review and install the recommended extensions with the Extensions: Show Recommended Extensions command or by clicking on the extentions tab on left side of the window and selecting "Workspace Recommendations".

.. note::

    To deploy the Lakeflow Framework to your Databricks workspace, follow the steps in :doc:`deploy_framework`.
