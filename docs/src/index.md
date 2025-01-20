Grana Documentation
===================

`grana` is an open-source command-line declarative automation tool,
whose purpose is launching pipelines easily in any environment from the local machine to the automation server.

> The original philosophy of Grana is to provide the following features:
> - An executable unit is a declaratively described pipeline, which is called a *Workflow*. 
> - Workflows may consist of sequential as well as of concurrent steps.
> - Workflow steps (herein referred to as *Actions*) can produce return values to be reused in subsequent actions.
> - Actions can interact with the user, but only in one direction (that is, an action can generate visible output).
> - Actions are parametrized, and parameters can be results of lazy evaluation of expressions.
> - Custom action types can be created by implementing a very simple interface.
>
> And here we are.


```{toctree}
:caption: Contents
:maxdepth: 2
user_guide/index
developers_guide/index
```
