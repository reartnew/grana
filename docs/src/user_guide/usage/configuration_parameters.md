Configuration parameters
========================

## LOG_LEVEL
:::{list-table}
:widths: 1 2
*   - **Description**
    - Logging subsystem level
*   - **Type**
    - String
*   - **Command-line argument**
    - `--log-level`
*   - **Environment variable**
    - `GRANA_LOG_LEVEL`
*   - **Default**
    - `ERROR`
:::

## LOG_FILE
:::{list-table}
:widths: 1 2
*   - **Description**
    - Log file path
*   - **Type**
    - String
*   - **Environment variable**
    - `GRANA_LOG_FILE`
:::

## ENV_FILE
:::{list-table}
:widths: 1 2
*   - **Description**
    - Path where to look for a dotenv file to load.
*   - **Type**
    - String
*   - **Environment variable**
    - `GRANA_ENV_FILE`
*   - **Default**
    - `./.env`
:::
 
## INTERACTIVE_MODE
:::{list-table}
:widths: 1 2
*   - **Description**
    - Specifies whither to run plan interaction phase or not.
*   - **Type**
    - Boolean
*   - **Command-line argument**
    - `--interactive`
*   - **Default**
    - `False`
:::

## WORKFLOW_SOURCE_FILE
:::{list-table}
:widths: 1 2
*   - **Description**
    - Workflow source file path.\
      When not set, `grana.yml`/`grana.yaml` are being looked for in the working directory.\
      If set to `-`, then standard input stream is used as the source.
*   - **Type**
    - String
*   - **Command-line argument**
    - Positional argument to `grana run` and `grana validate`
*   - **Environment variable**
    - `GRANA_WORKFLOW_FILE`
:::

## WORKFLOW_LOADER_CLASS
:::{list-table}
:widths: 1 2
*   - **Description**
    - Path to python file containing custom loader class to use.
*   - **Type**
    - String
*   - **Environment variable**
    - `GRANA_WORKFLOW_LOADER_SOURCE_FILE`
:::

## ACTION_CLASSES_DIRECTORIES
:::{list-table}
:widths: 1 2
*   - **Description**
    - Directories to scan for custom action definitions.
*   - **Type**
    - List of directories
*   - **Environment variable**
    - `GRANA_ACTIONS_CLASS_DEFINITIONS_DIRECTORY` (colon-separated paths)
:::

## DISPLAY_CLASS
:::{list-table}
:widths: 1 2
*   - **Description**
    - Display class to use.
*   - **Type**
    - `grana.display.base.BaseDisplay`
*   - **Command-line argument**
    - `display`
*   - **Environment variable**
    - `GRANA_DISPLAY_SOURCE_FILE` (path to custom display module file)\
      `GRANA_DISPLAY_NAME` (predefined display name)
*   - **Default**
    - `prefixes`
:::

## STRATEGY_CLASS
:::{list-table}
:widths: 1 2
*   - **Description**
    - Strategy class to use.
*   - **Type**
    - `grana.strategy.BaseStrategy`
*   - Workflow `configuration` section key
    - `strategy`
*   - **Command-line argument**
    - `strategy`
*   - **Environment variable**
    - `GRANA_STRATEGY_NAME`
*   - **Default**
    - `explicit`
:::

## USE_COLOR
:::{list-table}
:widths: 1 2
*   - **Description**
    - Forces using of ANSI color codes in the output.
*   - **Type**
    - Boolean
*   - **Environment variable**
    - `GRANA_FORCE_COLOR`
*   - **Default**
    - Depends on the TTY presence.
:::

## SHELL_INJECT_YIELD_FUNCTION
:::{list-table}
:widths: 1 2
*   - **Description**
    - Defines whether to add internal function definitions to the `shell` action or not.
*   - **Type**
    - Boolean
*   - **Environment variable**
    - `GRANA_SHELL_INJECT_YIELD_FUNCTION`
*   - **Default**
    - `True`
:::

## STRICT_OUTCOMES_RENDERING
:::{list-table}
:widths: 1 2
*   - **Description**
    - Defines whether to fail on an attempt of rendering of a non-existent outcome key or not.
*   - **Type**
    - Boolean
*   - **Environment variable**
    - `GRANA_STRICT_OUTCOMES_RENDERING`
*   - **Default**
    - `False`
:::

## DEFAULT_SHELL_EXECUTABLE
:::{list-table}
:widths: 1 2
*   - **Description**
    - Default shell executable for the `shell` action.
*   - **Type**
    - String
*   - **Environment variable**
    - `GRANA_DEFAULT_SHELL_EXECUTABLE`
*   - **Default**
    - `/bin/sh`
:::
