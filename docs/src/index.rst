Grana Documentation
===================

Grana is an open-source command-line declarative automation tool, whose purpose is launching pipelines easily in any environment from the local machine to the automation server.

The original philosophy of the project is to provide the following features:
   - A pipeline may consist of sequential as well as of concurrent steps.
   - Pipeline steps (herein referred to as Actions) can interact with the user, but only in one direction (that is, a step can produce visible output).
   - Actions can produce output to be reused in subsequent actions.
   - Actions are parametrized, and parameters may be dynamic.
   - Parameters can be results of expressions lazy evaluation.
   - When there is such a need, a custom action can be created by implementing a very simple interface.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

