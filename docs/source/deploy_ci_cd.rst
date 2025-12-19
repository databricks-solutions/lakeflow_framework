Setting up CI/CD
#################


This section describes the required general steps in a CI/CD pipeline to deploy the framework bundle.
For specific CI/CD platform example using GitHub Actions, see https://docs.databricks.com/en/dev-tools/bundles/ci-cd-bundles.html

Prerequisites and Assumptions
----------------------------
1. You have a Databricks access token for the CI/CD agent to authenticate to your Databricks workspace.
2. CI/CD agent has python and git installed.
3. CI/CD agent has access to the framework bundle repository.


Main Steps in a CI/CD Pipeline
-----------------------------
1. Install Databricks CLI
    If the CI/CD agent you are using is not already using an image which has Databricks cli installed, you can install it using curl:

.. code-block:: bash

    curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh


2. Confirm Databricks CLI is installed

.. code-block:: bash

    databricks --version


3. Configure Databricks CLI

.. code-block:: bash

    export DATABRICKS_HOST="https://<workspace-url>"
    
    export DATABRICKS_TOKEN="<pat-token>"
    or 
    export DATABRICKS_CLIENT_ID="<databricks-client-id>"
    export DATABRICKS_CLIENT_SECRET="<databricks-client-secret>"

4. Clone the framework bundle repository

.. code-block:: bash

    git clone https://github.com/databricks/framework-bundle.git

5. Install dependencies for bundle validation

.. code-block:: bash

    pip install -r requirements.txt

6. Validate bundle configuration

.. code-block:: bash

    databricks bundle validate

7. Deploy current version

.. code-block:: bash

    databricks bundle deploy --var="version=current" -t $ENVIRONMENT

8. Deploy specific version for rollback

.. code-block:: bash

    databricks bundle deploy --var="version=[version-number]" -t $ENVIRONMENT


Example CI/CD bash script
--------------------
Here's an example deployment script that can be used in your CI/CD pipeline:

.. code-block:: bash

    #!/bin/bash
    set -e

    # Script arguments
    ENVIRONMENT=${1:-dev}  # Default to dev if not specified
    FRAMEWORK_VERSION=${2:-1.2.3}  # Default version for rollback if not specified

    # Install Databricks CLI if not already installed
    if ! command -v databricks &> /dev/null; then
        echo "Installing Databricks CLI..."
        curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
    fi

    # Verify Databricks CLI installation
    databricks --version

    # Verify required environment variables are set
    if [ -z "$DATABRICKS_HOST" ] || { [ -z "$DATABRICKS_TOKEN" ] && [ -z "$DATABRICKS_CLIENT_ID" ]; }; then
        echo "Error: Required environment variables not set"
        echo "Please set:"
        echo "  DATABRICKS_HOST"
        echo "  DATABRICKS_TOKEN or (DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET)"
        exit 1
    fi

    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt

    # Validate bundle configuration
    echo "Validating bundle configuration..."
    databricks bundle validate

    # Deploy current version
    echo "Deploying current version to $ENVIRONMENT..."
    databricks bundle deploy --var="version=current" -t $ENVIRONMENT

    # Deploy specific version for rollback
    echo "Deploying version $FRAMEWORK_VERSION to $ENVIRONMENT for rollback..."
    databricks bundle deploy --var="version=$FRAMEWORK_VERSION" -t $ENVIRONMENT

    echo "Deployment complete!"
