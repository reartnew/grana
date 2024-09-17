# grana

Grana is an extensible declarative task runner,
aimed to make complex routine jobs easier to configure.

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/grana)](https://pypi.python.org/pypi/grana/)
[![License](https://img.shields.io/pypi/l/grana.svg)](https://opensource.org/license/mit/)
[![PyPI version](https://badge.fury.io/py/grana.svg)](https://pypi.python.org/pypi/grana/)
[![Tests](https://github.com/reartnew/grana/workflows/main/badge.svg)](https://github.com/reartnew/grana/actions/workflows/main.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Coverage Status](https://coveralls.io/repos/github/reartnew/grana/badge.svg?branch=main)](https://coveralls.io/github/reartnew/grana?branch=main)

<details>
  <summary>Table of Contents</summary>

1. [Installation](#installation)
2. [Usage](#usage)
3. [How to contribute](#contribute)

</details>

<div id="installation"></div>

## Installation

```shell
# Install only core components
pip install grana

# Install with all extensions
pip install "grana[all]"
```

<div id="usage"></div>

## Usage

#### Basic examples

```shell
# Execute a workflow that is outlined
# in the workdir-located grana.yaml file
grana run

# Print usage
grana --help
```

Options are configured either via environment variables or via command-line switches. The most common are:

- `GRANA_LOG_LEVEL`: Set log level.
- `GRANA_LOG_FILE`: Set log file.
- `GRANA_WORKFLOW_FILE`: Set the workflow file path explicitly.
- `GRANA_STRATEGY_NAME`: Manage execution strategy.
- `GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY`: Where to look for custom action runners.
- `GRANA_STRICT_OUTCOMES_RENDERING`: Manage failure behaviour when an outcome key is missing.

Full list of used environment variable names can be obtained with this command:

```shell
grana info env-vars
```

<div id="contribute"></div>

## How to contribute

#### Development environment setup

Requires system-wide poetry>=1.3.2, see [official documentation](https://python-poetry.org).

```shell
poetry env use python3.8
poetry install --no-root --sync --all-extras
```

The root directory for the source code is `src`,
thus one may add it to the project's python path
for better IDE integration.

#### Running tests with coverage on current environment

```shell
poetry run pytest --cov --cov-report=html:.coverage_report
```

#### Running tests on all available environments

```shell
poetry run tox
```
