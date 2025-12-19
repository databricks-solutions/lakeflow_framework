Deploying the Framework
###########################

.. _local_deployment:

Deploying From Your Local Machine
=================================

The steps below will guide you through deploying the Lakeflow Framework to your Databricks workspace and assume you have cloned the Lakeflow Framework repository and are in the root directory of the repository.

1. Ensure you have the Databricks CLI installed and configured. If not, please refer to the `Databricks CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_.
2. Ensure the correct Databricks workspace is set as the workspace host field in the databricks.yml file or ensure no host is set to use the default host confgured on the profile used by the Databricks CLI (Databricks CLI should be configured with credentials to access this workspace).
   databricks.yml file should look like this to add a host:

    .. code-block:: yaml

        bundle:
            name: dlt_framework

        include:
        - resources/*.yml

        targets:
        dev:
            mode: development
            default: true
            workspace:
            host: https://<your-databricks-workspace-url>

3. Run the following command from the root directoy to validate the Lakeflow Framework bundle:
   
    .. code-block:: console
        
        databricks bundle validate

   This command will run a series of checks to ensure the bundle is correctly set up and ready for deployment.
4. Run the following command to deploy the Lakeflow Framework to your Databricks workspace:
   
    .. code-block:: console
    
        databricks bundle deploy

5. Once the deployment is successful, you should see the Lakeflow Framework bundle in your Databricks workspace. 
   To varify, you can go to your Databricks workspace and check if the bundle is present in the ``.bundle`` directory.

.. Note::
   Databricks CLI will deploy the bundle to the default target workspace (usually dev by default) specified in the databricks.yml file. If you want to deploy the bundle to a different tagret, you can specify the target host using the ``-t`` option in the deploy command.
   Databricks CLI will deploy using default credentials. If you want to deploy using a different set of credentials, you can specify the profile using the ``-p`` option in the deploy command.

.. _ci_cd_deployment:

Deploying via CI/CD
===================
Please refer to the CI/CD documentation for more information on how to deploy the Lakeflow Framework samples using CI/CD.
