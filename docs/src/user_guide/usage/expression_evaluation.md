Expression evaluation
=====================

Expressions are a powerful way to parametrize your actions.
Each action arguments are evaluated right before the action starts in the way described below.

:::{important}
The following examples are relevant for the default YAML loader.\
For custom loaders, refer the developers guide.
:::

:::{contents} On this page:
:depth: 1
:local:
:backlinks: none
:::

## Expression structure

Expressions are literally pythonic with lazy evaluation, and there are the following objects available:

- `context` (aliased as `ctx`): references to the workflow [context map](./workflow_structure.md#context).
- `environment` (aliased as `env`): provides access to environment variables.
- `outcomes` (aliased as `out`): contains finished actions [outcome values](./actions/index.md#outcomes).
- `metadata` (aliased as `meta`): a bunch of workflow metadata information.

:::{tip}
Each of these containers are python dictionaries, which allow attribute access to their fields.
E.g. `env.HOME` is a valid way to read the `HOME` environment variable.
:::

## Use cases

Expressions can *only* be used in:

- Action arguments
- Context fields

## YAML expression reference type

To define an expression with the arbitrary value type, a special YAML tag is introduced: `!@`.
The following data must be a string with the desired expression. Let's proceed to an example right away:

```yaml
context:
  firstEnvMap:
    GRANA_TEST_VAR_1: foo
  secondEnvMap:
    GRANA_TEST_VAR_2: bar
  combinedEnvMap: !@ "{ **ctx.firstEnvMap, **ctx.secondEnvMap }"
actions:
  
  # This action will succeed
  - type: shell
    environment: !@ ctx.combinedEnvMap
    command: |
      set -e
      env
      if [ "$GRANA_TEST_VAR_1" != "foo" ]; then exit 1; fi
      if [ "$GRANA_TEST_VAR_2" != "bar" ]; then exit 2; fi
```

## YAML scalar string type

When in need to use expression evaluation for rendering a string, one may use the `@{...}` syntax.
Each string that is suitable for rendering (see [](#use-cases)) is preprocessed during action render phase.
This processing involves replacing all occurrences of curly braces prepended by an `@` sign,
directly evaluating the inner expression and casting it into a python string.

For example, evaluating the `"I am @{ env.USER.capitalize() }!"` YAML string literal
within `alice` user session produces the following: `I am Alice!`.
