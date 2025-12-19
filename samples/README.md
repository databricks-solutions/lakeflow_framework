# The Samples

The Framework comes with extensive samples that demonstrate the use of the framework and Lakeflow concepts. At the time of writing, sample are organized into the following bundles:

* Bronze
* Silver
* Gold
* Test Data and Orchestrator
* TPC-H

The samples broadly break down into the following:

| Sample Type | Folder | Description |
|-------------|--------|-------------|
| **Base and Pattern Samples** | - `<bundle>/src/dataflows/base_samples`<br>- `<bundle>/src/dataflows/<pattern_name>` | Bronze, Silver and Gold samples that demonstrate the patterns and data examples used in the patterns section of the documentation |
| **Feature Samples** | `<bundle>/src/dataflows/feature_samples` | Sample per key feature |
| **Kafka Samples** | `<bundle>/src/dataflows/kafka_samples` | Base Kafka, Confluent schema registry and SQL off Kafka samples |
| **TPC-H Sample** | Separate bundle for TPC-H samples | Based on TPC-H schema in UC samples catalog, reverse engineered to demonstrate end to end streaming data warehouse |

## Deploying the Samples

The samples can be deployed using the scripts located in the `samples` directory:

* `deploy.sh`: Deploys all the samples execpt for TPC-H.
* `deploy_bronze.sh`: Deploys only the bronze samples.
* `deploy_silver.sh`: Deploys only the silver samples.
* `deploy_gold.sh`: Deploys only the gold samples.
* `deploy_orchestrator.sh`: Deploys only the test data and orchestrator bundle.
* `deploy_tpch.sh`: Deploys only the TPC-H sample.

### Prerequisites:

* Databricks CLI installed and configured
* Lakeflow framework already deployed to your workspace (see deploy_framework)

### Interactive Deployment

1. Navigate to the samples directory in the root of the Framework repository:

   ```console
   cd samples
   ```

2. Run the desired deploy script:

   ```console
   ./deploy.sh
   ```

3. Follow the prompts to deploy the samples.

   * **Databricks username**: Your Databricks username in the workspace you are deploying to e.g. `jane.doe@company.com`.
   * **Databricks workspace**: The full URL of the workspace you are deploying to e.g. `https://company.cloud.databricks.com`.
   * **Databricks CLI profile**: The Databricks CLI profile you want to use for the deployment. Default: `DEFAULT`.
   * **Select Compute**: Select between Classic/Enhaced or Serverless compute (0=Enhanced, 1=Serverless). Default: `1`.
   * **UC Catalog**: The Unity Catalog you want to use for the deployment. Default: `main`.
   * **Schema Namespace**: The first part of the name for the bronze, silver and gold schemas. Default: `lakeflow_samples`.
   * **Logical environment**: The logical environment you want to use for the deployment e.g. `_test`.

   > **Important:**
   >
   > Always specify a logical environment when deploying the samples, this ensures you don't anyone elses existing samples in the workspace, as long as the logical environment is unique.
   >
   > Suggested naming:
   >
   > * Your initials, e.g Jane Doe would be `_jd`
   > * A Story ID, e.g `123456` would be `_123456`
   > * Your client name, e.g Company would be `_client`
   > * Others: business unit, team name, project name, etc...

4. Once deployment is complete, you can find the deployed bundles under `/Users/<username>/.bundle/`

### Single Command line deployment:

1. Navigate to the samples directory in the root of the Framework repository:

   ```console
   cd samples
   ```

2. Run the desired deploy script with required parameters:

   ```console
   ./deploy.sh -u <databricks_username> -h <workspace_host> [-p <profile>] [-l <logical_env>] [--catalog <catalog>]
   ```

   Parameters:
   
   * `-u, --user`: Your Databricks username (required)
   * `-h, --host`: Databricks workspace host URL (required)
   * `-p, --profile`: Databricks CLI profile (optional). Default: `DEFAULT`.
   * `-c, --compute`: The type of compute to use (0=Enhanced, 1=Serverless). Default: `1`.
   * `-l, --logical_env`: Logical environment suffix for schema names (optional). Default: `_test`.
   * `--catalog`: Unity Catalog name (optional). Default: `main`.
   * `--schema_namespace`: Overide the first part of the name for the bronze, silver and gold schemas (optional). Default: `lakeflow_samples`.
   
   For example:

   ```console
   ./deploy.sh -u jane.doe@company.com -h https://company.cloud.databricks.com -l _jd
   ```

4. Once deployment is complete, you can find the deployed bundles under `/Users/<username>/.bundle/`

## Using the Samples

### Test Data and Orchestrator

The Test Data and Orchestrator bundle includes:

* Test data initialization and load simulation
* Multiple job to simulate end to end runs of the samples

#### Jobs

After deployment you should find the following jobs in your workspace:

* Lakeflow Framework Samples - Run 1 - Load and Schema Initialization
* Lakeflow Framework Samples - Run 2 - Load
* Lakeflow Framework Samples - Run 3 - Load
* Lakeflow Framework Samples - Run 4 - Load

These will be prefixed with the target and your username and suffixed with the logical environment you provided when deploying the samples.

For example:
`[dev jane_doe] Lakeflow Framework Samples - Run 1 - Load and Schema Initialization (_jd)`

To execute the samples, simply execute the jobs in order to simulate the end to end run of the samples over the test data.

#### Pipelines

You can also of course execute individual pipelines as well, these also follow a similiar name convention with `Lakeflow Samples` in the name.

## Destroying the Samples

To destroy the samples, you can use the `destroy.sh` script following the command specified below.

```console
./destroy.sh -h <workspace_host> [-p <profile>] [-l <logical_env>]
```

Parameters:
   
* `-h, --host`: Databricks workspace host URL (required)
* `-p, --profile`: Databricks CLI profile (optional, defaults to DEFAULT)
* `-l, --logical_env`: Logical environment suffix for schema names (optional)

## TPC-H Sample

The TPC-H sample is based off the TPC-H schema in the UC catalog and reverse engineered to demonstrate end to end streaming data warehouse.

To deploy the TPC-H sample, you can use the `deploy_tpch.sh` script following the same methods specified above.

This sample is currently still being built with an initial cut targetted for Sept 2025.