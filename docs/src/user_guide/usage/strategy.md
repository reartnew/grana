Strategy
========

A `strategy` is an iterator that is responsible for controlling actions execution order.
Default is [](#auto).

:::{contents} On this page:
:depth: 2
:local:
:backlinks: none
:::

## Dependency types
A *dependency* is a relation between two actions, and it can be either **strict** or not.
If an action has a strict dependency failed, then it is treated as skipped and is not executed.  

## Available strategies

:::{grana-strategies}
:::
