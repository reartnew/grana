Getting started
=================

```{attention}
Since Grana is a CLI tool,
this section covers command-line scenarios only.
```

```{contents} On this page:
   :depth: 1
   :local:
   :backlinks: none
```

## Running your first workflow

Simple workflows can be executed without any configuring grana.
Create a `grana.yaml` file in the working directory with the following contents:
```yaml
---
actions:
  - name: ShellCheck
    type: shell
    command: echo "Grana works!"
```
Then, staying in the same directory, call a command:
```shell
$ grana run
```

The produced output should look like this:
```
[ShellCheck]  | Grana works!
✓ SUCCESS: shell-0
```
