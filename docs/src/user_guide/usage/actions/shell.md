`shell` - execute shell script
=============================

```{note}
This article is about a specific individual action.

On how to call actions in general, refer to [Calling actions](./index).
```

:::{list-table} 
:widths: 1 1 4
:header-rows: 1

*   - Parameter
    - Type
    - Description
*   - `command`
    - **string**

      *optional*
    - Shell script text to execute.

      Required, when `file` parameter is unfilled.
*   - `file`
    - **string**

      *optional*
    - Shell script file to execute.

      Required, when `command` parameter is unfilled.
*   - `environment`
    - **mapping**

      *keys: string*

      *values: string*

      *optional*
    - Environment variable names and values to be added to the launched shell.
*   - `cwd`
    - **string**

      *optional*
    - Working directory to set for the launched shell.
*   - `executable`
    - **string**

      *optional*
    - Path to the shell binary.

      See also: default shell executable. 
:::
