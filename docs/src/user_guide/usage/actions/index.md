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

## Status

Any action has a defined *status*, which is one of the following:

:::{list-table}
:widths: 1 4
:header-rows: 1
*   - Status
    - Meaning
*   - *PENDING*
    - The action is scheduled, but has not started yet.
*   - *RUNNING*
    - The action is being executed.
*   - *SUCCESS*
    - The action has finished without errors.
*   - *WARNING*
    - The action has failed, but has low severity.
*   - *FAILURE*
    - The action has failed.
*   - *SKIPPED*
    - The action has either called a `skip` method or had a failed/skipped strict dependency.
*   - *OMITTED*
    - The action is not scheduled (e.g. was disabled during the plan interaction phase).
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
