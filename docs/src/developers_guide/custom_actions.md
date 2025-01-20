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
