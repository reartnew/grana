Grana Documentation
===================

Grana is an open-source command-line declarative automation tool,
whose purpose is launching pipelines easily in any environment from the local machine to the automation server.

The original philosophy of the project is to provide the following features:

- An executable unit is called **Workflow**, which is a declaratively described pipeline.
- Workflows may consist of sequential as well as of concurrent steps.
- Workflow steps (herein referred to as **Actions**) can produce return values to be reused in subsequent actions.
- Actions can interact with the user, but only in one direction (that is, an action can generate visible output).
- Actions are parametrized, and parameters can be results of lazy evaluation of expressions.
- Custom action types can be created by implementing a very simple interface.

```{warning}
This theme is still under active development, and we make no promises
about the stability of any specific HTML structure, CSS variables, etc.
Make these customizations at your own risk, and pin versions if you're
worried about breaking changes!
```

```{toctree}
:caption: Get started

install
```