`loop` - run an action within a loop
====================================

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
This action executes another action in the repetitive manner.
Failure criteria for the step are the same as for a [subflow](./subflow) step,
since the action is actually translated into one.

## Parameters
:::{list-table}
:widths: 1 1 4
:header-rows: 1
*   - Name
    - Type
    - Description
*   - `step`
    - **mapping**\
      *required*
    - Action specification to be executed within the loop.\
      **Note**: only `type` and `name` reserved fields can be used inside the `step` definition,
      but all action-specific arguments are allowed.
*   - `matrix`
    - **mapping**\
      *required*\
      *keys: string*\
      *values: iterable*
    - Loop variables definitions, e.g. `i: !@ range(5)`.\
      Multiple variables can be provided.
      If so, then the cartesian product of all specified ranges is used to produce the loop.\
      Corresponding variables values are available in the `locals` namespace within the step.\
      **Note**: eponymous local keys set from the **locals** directive will be replaced.
*   - `strategy`
    - **string**\
      *optional*
    - Explicitly set strategy to be used within the loop subflow.\
      When not set, base workflow value is used.\
      Allowed values are listed on the [corresponding page](../strategy). 
*   - `strict`
    - **boolean**\
      *optional*
    - Explicitly set dependency mode to be used within the loop subflow.\
      When not set, base workflow value is used.\
      See more about dependencies strictness [here](../strategy). 
:::

## Outcomes injection

Basically the same as for the [subflow](./subflow) action type.

##
