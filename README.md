# grana

Grana is an open-source command-line task automation tool,
whose purpose is launching pipelines easily in any environment from the local machine to the automation server.

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/grana)](https://pypi.python.org/pypi/grana/)
[![License](https://img.shields.io/pypi/l/grana.svg)](https://opensource.org/license/mit/)
[![PyPI version](https://badge.fury.io/py/grana.svg)](https://pypi.python.org/pypi/grana/)
[![Tests](https://github.com/reartnew/grana/workflows/main/badge.svg)](https://github.com/reartnew/grana/actions/workflows/main.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Coverage Status](https://coveralls.io/repos/github/reartnew/grana/badge.svg?branch=main)](https://coveralls.io/github/reartnew/grana?branch=main)

## Get started

#### Installation
Grana can be installed using the python package manager of your choice, e.g. `pip`:
```shell
$ pip install grana
```
For more details, see the [Installation guide](https://grana.readthedocs.io/en/latest/user_guide/install.html).

#### Usage examples

```shell
$ grana run workflow.yaml
```

Take a look at the [usage documentation](https://grana.readthedocs.io/en/latest/user_guide/usage) also.
## Documentation

You're welcome to read the documentation at [grana.readthedocs.io](https://grana.readthedocs.io/en/latest/index.html).

## Contributing

#### Development environment setup

Requires *poetry>=1.8.3*, see [official documentation](https://python-poetry.org).

```shell
$ poetry env use python3.11
$ poetry install --sync --all-extras
```

#### Running tests with coverage on current environment

```shell
$ poetry run pytest --cov --cov-report=html:.coverage_report
```

#### Running tests on all available environments

```shell
$ poetry run tox
```

#### Running docs builder development server
```shell
$ poetry run sphinx-autobuild -aEWb html docs/src docs/dist
```
