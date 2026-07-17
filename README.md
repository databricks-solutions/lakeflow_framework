# Databricks Lakeflow Framework

[![Docs](https://img.shields.io/badge/docs-live-brightgreen)](https://databricks-solutions.github.io/lakeflow_framework/)
[![CI](https://github.com/databricks-solutions/lakeflow_framework/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/databricks-solutions/lakeflow_framework/actions/workflows/ci.yml?query=branch%3Amain)
[![Release](https://img.shields.io/github/v/release/databricks-solutions/lakeflow_framework)](https://github.com/databricks-solutions/lakeflow_framework/releases)
[![License](https://img.shields.io/badge/license-Databricks%20License-blue)](https://github.com/databricks-solutions/lakeflow_framework/blob/main/LICENSE.md)

<!-- Top bar will be removed from PyPi packaged versions -->
<!-- Dont remove: exclude package -->
[Documentation](https://databricks-solutions.github.io/lakeflow_framework/) |
[Sample Data Bundles](samples)
<!-- Dont remove: end exclude package -->

## Project Description

The Lakeflow Framework is a metadata-driven framework for building Databricks Lakeflow Spark Declarative Pipelines. It uses a configuration-driven, pattern-based approach to support both batch and streaming workloads across the medallion architecture.

The framework supports centralized and domain-oriented operating models, and accommodates multiple modelling paradigms (including dimensional, Data Vault, and enterprise canonical models). It is designed for simplicity, performance, maintainability, and extensibility as the Databricks product evolves.

## Why use Lakeflow Framework

- Configuration-driven pattern based pipeline delivery with reusable implementation patterns
- Support for batch and streaming pipelines across Bronze/Silver/Gold, aligned to your chosen modelling pattern
- Flexible for centralized and domain-oriented operating models

## Prerequisites

- Access to a Databricks workspace
- Databricks CLI installed and authenticated (`databricks auth login` for your workspace, or a configured CLI profile)
- Familiarity with Databricks Lakeflow Spark Declarative Pipelines concepts

## Quick start

Deploy the framework:

```bash
git clone https://github.com/databricks-solutions/lakeflow_framework.git
cd lakeflow_framework
databricks bundle deploy -t dev
```

Deploy samples (requires the framework above): see [samples/README.md](samples/README.md) for bundle descriptions and deploy scripts (`deploy.sh`, `deploy_feature_samples.sh`, `deploy_tpch.sh`, and others).

```bash
cd samples
./deploy.sh
```

Full deployment steps, configuration options, and walkthroughs are in the public docs [Getting Started](https://databricks-solutions.github.io/lakeflow_framework/current/getting_started.html) section.

## Repository structure

- `docs/` — Sphinx documentation and versioned docs build tooling
- `samples/` — example framework and pipeline bundles
- `src/` — framework bundle root deployed to the workspace (`framework.sourcePath` in DAB)
  - `lakeflow_framework/` — canonical Python package: runtime code, bundled default config (`config/default/`), and JSON schemas (`schemas/`). Prefer `from lakeflow_framework...` imports in new code.
  - `*.py` at `src/` root — backward-compatibility shims for legacy bare imports (e.g. `from constants import ...`); removed at v1.0.0
  - `local/` — customer-owned sparse config and extensions; never overwritten by upstream upgrades ([src/local/README.md](src/local/README.md))

See [Import conventions](https://databricks-solutions.github.io/lakeflow_framework/contributor_imports.html)

## Version compatibility

This project tracks Databricks Lakeflow Spark Declarative Pipelines capabilities and evolves with platform changes. Validate runtime, feature, and API compatibility against your target Databricks workspace and the latest project documentation before production rollout.

## Project status and support

The framework is actively maintained. Databricks support does not cover this repository; issue support is best effort through GitHub issues.

## Releases and changelog

- Releases: https://github.com/databricks-solutions/lakeflow_framework/releases
- Tags: https://github.com/databricks-solutions/lakeflow_framework/tags

## Documentation

Please refer to the [documentation](https://databricks-solutions.github.io/lakeflow_framework/) for further details and an explanation of the samples.
The documentation needs to be deployed as HTML or Markdown within your org before it can be used.

### Local development quick start (contributors)

Clone the repository, then set up a Python 3.12 environment. This is a minimal local quick start — full contributor guidance (VS Code setup, lockfiles, deployment, and PR workflow) is in the documentation under **Framework Development & Contributors**.

```bash
git clone https://github.com/databricks-solutions/lakeflow_framework.git
cd lakeflow_framework
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --require-hashes --no-deps -r requirements-dev.lock
```

For editable installs and IDE auto-complete: `pip install -e ".[contrib]"` (see [Development Environment Setup](https://databricks-solutions.github.io/lakeflow_framework/contributor_dev_env.html)).

Run unit tests:

```bash
pytest tests/ -m "not integration and not spark"
```

See also `tests/README.md` and `docs/source/contributor_imports.rst` in the repository.

### Local docs development (optional)

Requires dev dependencies from `requirements-dev.lock`:

```bash
make -C docs html
```

## How to get help

Databricks support doesn't cover this content. For questions or bugs, please open a GitHub issue and the team will help on a best effort basis.

## License

&copy; 2025 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the Databricks License [https://databricks.com/db-license-source].  All included or referenced third party libraries are subject to the licenses set forth below.
