# Databricks Lakeflow Framework

[![Docs](https://img.shields.io/badge/docs-live-brightgreen)](https://databricks-solutions.github.io/lakeflow_framework/)
[![Main Build](https://github.com/databricks-solutions/lakeflow_framework/actions/workflows/main-build.yml/badge.svg?branch=main&event=push)](https://github.com/databricks-solutions/lakeflow_framework/actions/workflows/main-build.yml?query=branch%3Amain)
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

## Quick start

```bash
git clone https://github.com/databricks-solutions/lakeflow_framework.git
cd lakeflow_framework
pip install -r requirements-dev.txt
```

Then:

1. Open the hosted docs: https://databricks-solutions.github.io/lakeflow_framework/
2. Deploy the framework using the `Deploy Framework` guide
3. Deploy samples from `samples/` using the documentation walkthroughs
4. Build your first pipeline bundle using the `Build a Pipeline Bundle` guide

## Prerequisites

- Access to a Databricks workspace
- Databricks CLI installed and configured
- Python environment with project dependencies installed
- Familiarity with Databricks Lakeflow Spark Declarative Pipelines concepts

## Repository structure

- `docs/` - Sphinx documentation and versioned docs build tooling
- `samples/` - example framework and pipeline bundles
- `src/` - framework source code and runtime components

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

### Local docs development (optional)

```bash
pip install -r requirements-docs.txt
make -C docs html
```

## How to get help

Databricks support doesn't cover this content. For questions or bugs, please open a GitHub issue and the team will help on a best effort basis.

## License

&copy; 2025 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the Databricks License [https://databricks.com/db-license-source].  All included or referenced third party libraries are subject to the licenses set forth below.
