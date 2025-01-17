Workflow structure
==================

The article explains the structure of a workflow in detail.

:::{important}
The following examples are relevant for the default YAML loader.\
For custom loaders, refer the developers guide.
:::

:::{contents} On this page:
   :depth: 3
   :local:
   :backlinks: none
:::

## Structure

A typical workflow source is a YAML document, containing a mapping with the fields described below.
Any other fields or document types are rejected by default.

### `actions`
Represents a list of mappings, each of which define an [action](../actions/index.md).
The mapping structure is:
:::{list-table}
:widths: 1 4
:header-rows: 1
*   - Key
    - Description
*   - `type`\
      *{sub}`required,`*\
      *{sup}`type: string`*
    - Defines what and how this action does.\
      To get the list of delivered types, see [](../actions/index.md#action-types-index).\
      On how to define a custom type, go to the developers guide.
*   - `name`\
      *{sub}`optional,`*\
      *{sup}`type: string`*
    - A unique identifier for the workflow step.\
      If none given, then it's generate automatically.
*   - `description`\
      *{sub}`optional,`*\
      *{sup}`type: string`*
    - Text description of the action.\
      Used in several scenarios for displaying extra info on the action,
      e.g. during the plan interaction phase.
*   - `expects`\
      *{sub}`optional,`*\
      [*{sup}`type: see below`*](#expects-field)
    - Defines direct dependencies for the action.\
      Default is an empty list.\
      **An important note**: some strategies may ignore the value of this field.
*   - `selectable`\
      *{sub}`optional,`*\
      *{sup}`type: boolean`*
    - Specifies whether to allow switching the action on-off during plan interaction phase.\
      Defaults to `True`.
*   - `severity`\
      *{sub}`optional,`*\
      *{sup}`type: string`*
    - Specifies whether to allow switching the action on-off during plan interaction phase.\
      Value should be one of: `normal`, `low`.\
      Defaults to `normal`.
:::

#### `expects` field
This field, when set, should be of one of the following types:
- *A list of mappings*: an item of this list is a mapping with the following fields:
  :::{list-table}
  :widths: 1 3
  :header-rows: 1
  *   - Key
      - Description
  *   - `name`\
        *{sub}`required,`*\
        *{sup}`type: string`*
      - A name of another action in the workflow.
  *   - `strict`\
        *{sub}`optional,`*\
        *{sup}`type: boolean`*
      - Force the dependency strictness.\
        When not set, it is determined by the Strategy. 
  :::
  ```yaml
  # An example of an action using mapping-type dependencies
  - name: ActionOne
    type: <...>
    expects:
      - name: ActionTwo
      - name: ActionThree
        strict: yes
  ```
- *A list of strings*: contains a list of another actions **names**, e.g.
  ```yaml
  # An example of an action using string-type dependencies
  - name: ActionOne
    type: <...>
    expects:
      - ActionTwo
      - ActionThree
  ```
- *A string*: fully equivalent to a list of one string, e.g.
  ```yaml
  # An example of an action setting a single dependency
  - name: ActionOne
    type: <...>
    expects: ActionTwo
  ```

### `context`

### `configuration`

## A comprehensive example

```yaml
---
configuration:
  strategy: strict  # Set the strategy explicitly for this workflow
context:
  greeting: "Hello, @{ ctx.user.name }!"  # A template with a reference to another context field 
  user:
    name: !@ env.USER
actions:

  - name: GreetUser
    description: Say hi to the user
    type: echo
    message: "@{ ctx.greeting }"

  - name: ReportCurrentWorkDir
    description: Print out the working directory
    type: shell
    command: |
      pwd
    expects:
      - name: GreetUser
        strict: no

  - name: CheckEnvironment
    description: Validate that use has the AWS_DEFAULT_REGION variable set
    type: shell
    severity: low
    command: |
      [ "$AWS_DEFAULT_REGION" != "" ] || exit 1
    expects: GreetUser
```
