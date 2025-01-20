Strategy
========

A `strategy` is an iterator that is responsible for controlling actions execution order.
Default is [](#explicit).

:::{contents} On this page:
:depth: 2
:local:
:backlinks: none
:::

## Dependency types
A *dependency* is a relation between two actions, and it can be either **strict** or not.
If an action has a strict dependency failed, then it is treated as skipped and is not executed.  

## Available strategies

### `explicit`

Actions are started immediately after their explicit dependencies have finished the execution.
If no dependencies given for an action, then it is scheduled to start in the very beginning of the workflow run.
Dependencies are treated as non-strict by default.

### `strict`

Same as [](#explicit), but dependencies are treated as strict by default.
   
### `free`

All actions are started immediately. All dependencies are ignored.

### `sequential`

Actions run one-by-one in the same order they are specified in the workflow.
Dependencies are treated as non-strict by default.

### `strict-sequential`

Same as [](#sequential), but dependencies are treated as strict by default.
