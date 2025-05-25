Developing custom actions
=========================

## Creating a new action type 

- If you haven't yet, take a decision where to store your action definitions.\
  It could be one directory or multiple.\
  Make sure this directory is listed among the [action class directories](../user_guide/usage/configuration_parameters.md#action_classes_directories).
- Give your new action type a good name.\
  It's recommended to be recognizable and unique.
- Create a file called `<your-new-type-name>.py` in your action definitions directory with the following backbone:
  ```python
  from grana import ActionBase, ArgsBase
  
  class Args(ArgsBase):
      """Here goes the arguments description"""
  
  class Action(ActionBase):
      args: Args

      async def run(self):
          """Here goes your logic"""
  ```

## About action arguments

Each action class has an `args` field, which is:
- Annotated with a python dataclass (typically a subclass of `grana.ArgsBase`).
- Populated for the instance by the workflow, based on the loaded information.

Subclasses of `grana.ArgsBase` are automatically dataclasses.\
Raw arguments ddata are transformed into dataclass instances according to intuitive logic.

## Action methods

:::{tip}
Grana leverages python `asyncio` functionality to implement tasks concurrency,
so be sure you module does not use long-running synchronous calls. 
:::

:::{function} run
:async: True
Main entry for any action. Return value is ignored.
:::

:::{function} say(message: str)
Sends a text to the display.
:::

:::{function} yield_outcome(key: str, value: Any)
Registers an outcome with the given *value* under the specified *key*.
:::

:::{function} skip
Terminates execution and sets the status to `SKIPPED`. 
:::

:::{function} fail(message: str = "")
Terminates execution with an optional message and sets the status to `FAILURE`.
:::
