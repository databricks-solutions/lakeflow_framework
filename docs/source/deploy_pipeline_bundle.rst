Deploying a Pipeline Bundle
##########################

.. _local_deployment:

Deploying From Your Local Machine
=================================

Once you have created a data pipeline bundle and deployed the Lakeflow Framework, you can deploy it to your Databricks workspace. 

1. Ensure you have the Databricks CLI installed and configured. If not, please refer to the `Databricks CLI documentation <https://docs.databricks.com/dev-tools/cli/index.html>`_.
2. Ensure the correct Databricks workspace is set as the workspace host field in the databricks.yml file (Databricks CLI should be configured with credentials to access this workspace).
3. Run the following command to validate the data pipeline bundle:
   
   .. code-block:: console

      databricks bundle validate
   This command will run a series of checks to ensure the bundle is correctly set up and ready for deployment.
4. Run the following command to deploy the data pipeline bundle to your Databricks workspace:
   
   .. code-block:: console
   
      databricks bundle deploy --var="pipeline_framework_path=/Workspace/Users/<your_databricks_user_id>/.bundle/<framework_bundle_name>/<environment>/current/files/src"
   The owner is your databricks user id.


5. Once the deployment is successful, you should see the data pipeline bundle in your Databricks workspace. 
   
   To varify, you can go to your Databricks workspace and check if the bundle is present in the ``.bundle`` directory.
   Also verify that a Spark Declarative Pipeline has been created in the Databricks workspace with the name of the pipeline being the name provided in the resources yaml file for the Spark Declarative Pipeline.

.. _ci_cd_deployment:

Deploying via CI/CD
===================
Please refer to the CI/CD documentation for more information on how to deploy the Lakeflow Framework samples using CI/CD.
