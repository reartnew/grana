Actions in a nutshell
=====================

An *Action* is the minimal executable unit of a workflow.

Each action has a *Type*, which defines the way it behaves.
An action does not control explicitly when to start (this is in the area of responsibility of the *Strategy*),
but one can require a dependency, which is a reference to another action.

:::{contents} On this page:
   :depth: 1
   :local:
   :backlinks: none
:::

## Outcomes

During the execution, an action can report named values, which are called *Outcomes*
and can later be reused as input for another actions. For an example of doing so,
refer to the shell [yield_outcome](./shell.md#helpers) function.

## Action types index
```{toctree}
:maxdepth: 1
echo
shell
subflow
```
