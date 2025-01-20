`shell` - execute shell script
=============================

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
This action allocates a shell and runs a script,
piping standard output/error streams to the end user.
The action is considered successful, when the return code of the shell equals zero.
By default, a few helper functions definitions are added (see [#helpers](#helpers)).

## Parameters
:::{list-table}
:widths: 1 1 4
:header-rows: 1
*   - Name
    - Type
    - Description
*   - `command`
    - **string**\
      *optional*
    - Shell script text to execute.\
      Required, when `file` parameter is unfilled.
*   - `file`
    - **string**\
      *optional*
    - Shell script file to execute.\
      Required, when `command` parameter is unfilled.
*   - `environment`
    - **mapping**\
      *optional*\
      *keys: string*\
      *values: string*
    - Environment variable names and values to be added to the launched shell.
*   - `cwd`
    - **string**\
      *optional*
    - Working directory to set for the launched shell.
*   - `executable`
    - **string**\
      *optional*
    - Path to the shell binary.\
      See also: default shell executable.
:::

## Helpers

:::{warning}
These functions rely on writing service messages to the standard output,
so redirecting may break their behaviour.
:::

When shell injection is enabled,
some predefined functions are available in the shell script.
These are:

:::{function} yield_outcome(name[, value])
  Report an outcome with the given name.
  If only the name is supplied, then the function reads the input for the value.
  Examples:
  ```bash
  # Registers an outcome named "foo" with value "bar"
  $ yield_outcome foo bar
  ```
  ```bash
  # Registers an outcome named "foo" with value of the data.txt file content
  $ cat data.txt | yield_outcome foo
  ```
:::

:::{function} skip()
  Terminate the shell immediately and set the corresponding action [status](./index.md#status) to `SKIPPED`.
  Ignores all given arguments.
  Example:
  ```bash
  $ skip
  ```
:::
