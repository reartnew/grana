`subflow` - run nested workflow
===============================

:::{note}
This article is about a specific action.\
On how to call actions in general, refer to [Calling actions](./index).
:::

:::{contents} On this page:
   :depth: 1
   :local:
   :backlinks: none
:::

## Overview
This action executes and independent workflow as a natural step.
Failure criteria for the step are the same as for any workflow:
some action failed, workflow source file not found, etc.

## Parameters
:::{list-table}
:widths: 1 1 4
:header-rows: 1
*   - Name
    - Type
    - Description
*   - `path`
    - **string**\
      *required*
    - Path to the workflow definition file.
*   - `context`
    - **mapping**\
      *optional*\
      *keys: string*\
      *values: any*
    - Context mapping to be merged into the workflow.\
      Merging is recursive: when both workflow and parameter-provided context fields on a certain level are mappings,
      the result is them combination of them, giving preference to the parameter-provided value.
      Otherwise, parameter-provided value prevails.
:::

## Outcomes injection

If a nested action yields an outcome,
the subflow action itself also produces an outcome with the same value,
but in a nested namespace:

```
[main workflow]
  ├─> [subflow "MySubFlow"]
  │     └─> [action "NestedAction"] ─> (yields "foo"="bar")
  └─> (may refer to "out.MySubFlow.NestedAction.foo", which equals "bar")
```
