<p align='center'>    
    <img width="40%" align='center' src="data/img/anci-light.png#gh-light-mode-only"/>
    <img width="40%" align='center' src="data/img/anci-dark.png#gh-dark-mode-only"/>
</p>

# anci

`anci` is a lightweight python package that automatically converts decorated, type-annotated functions into basic or hierarchical command-line interfaces.

## Installation

`anci` can be installed using `pip`

```bash
pip install anci
```

Or, added to your `pyproject.toml` using `uv`

```bash
uv add anci
```

## Usage

### Basic example

```python
from anci import Arg, base, cmd, main

@base("ops")
def ops():
    """Base command for 'ops'."""
    pass

@cmd("ops", "add")
def ops_add(
    x: Arg[int],                 # A flagged argument with no help text
    y: Arg[int, "Second."],      # A flagged argument with help text
    z: Arg[int, "Third."] = 100  # A flagged argument with help text and a default value
):
    """Print the sum of three numbers."""
    print(x + y + z)

if __name__ == "__main__":
    main("A CLI tool for basic math operations.")
```

This example demonstrates how to create a simple CLI using only decorators and type annotations:

- `@anci.base("ops")` - Creates a base command group called `ops` that initializes a hierarchy.
- `@anci.cmd("ops", "add")` - Registers subcommand `add` under `ops` with flagged arguments.
- `usage` - Usage info for each command (e.g. `ops --help`) are extracted from function docstrings.
- `anci.Arg` - Provides type hints and help text for each parameter.
- `anci.main()` - Automatically generates the CLI with help text, argument parsing, and command routing.

On the command-line, the `anci` command-line program can then be called as

```bash
python3 main.py ops add --help 
... usage: A CLI tool for basic math operations. ops add [-h] [--x X] [--y Y] [--z Z]
... 
... Print the sum of three numbers.
...
... options:
...   -h, --help  show this help message and exit
...   --x X
...   --y Y       Second.
...   --z Z       Third (default: 100).

python3 main.py ops add --x 2 --y 4
... 116

python3 main.py ops add --x 2 --y 4 --z 4
... 10
```

Or, if integrated as part of your python CLI package, then

```bash
package ops add --x 5 --y 3 --z 10
... 118
```

### Annotated example

`anci` currently provides support for various `annotated_types`, allowing automatic enforcement of range and boundary checks on integers, containers (such as lists, sets, and tuples), and strings.

```python
from anci import Arg, cmd, main
from anci.typing import Annotated, Gt, MaxLen

@cmd("types")
def check_my_types(
    x: Arg[list[str], "A list of strings."],
    y: Arg[Annotated[int, Gt(10)], "An integer greater than 10"],
    z: Arg[Annotated[set[float], MaxLen(2)], "A set of floats with a max of 2 elements"],
):
    """Print the types of each argument."""
    print("type length")
    print(type(x), len(x))
    print(type(y), 1)
    print(type(z), len(z))

if __name__ == "__main__":
    main("A CLI for checking types.")
```

This example shows how `anci` uses type annotations to handle complex types and enforce runtime checks:

- `x: Arg[list[str], ...]` - `anci` converts a sequence of letters into list of strings.
- `y: Arg[Annotated[int, Gt(10)], ...]`: `anci` verifies input integer is greater than 10.
- `y: Arg[Annotated[set[float], MaxLen(2)], ...]`: `anci` verifies set only has two elements.

When all arguments satisfy the runtime checks, the command runs without errors:

```bash
python main.py types --x a b c --y 11 --z 1
... type length
... <class 'list'> 3
... <class 'int'> 1
... <class 'set'> 1
```
However, since `anci` enforces range/length constraints directly from type annotations, the following produce errors:

```bash
python main.py types --x a b c --y 5 --z 1
... types: error: argument --y: y must be > 10, got 5

python main.py types --x a b c --y 11 --z 1 2 3
... types: error: argument --z: Expected at most 2 elements, got 3
```

## Supported type annotations

`anci` currently supports the following type annotations:

- Base types: `int`, `str`, `float`, `bool`, `bytes`, `pathlib.Path`
- Container types: `list[...]`, `List[...]`, `tuple[...]`, `Tuple[...]`, `set[...]`, `Set[...]`
- [`annotated_types`](https://github.com/annotated-types/annotated-types) (`typing.Annotated[...]`): `Gt`, `Ge`, `Lt`, `Le`, `Interval`, `MaxLen`, `MinLen`, `Len`.

All annotated types, and `pathlib.Path`, can be directly imported/aliased from `anci.typing` if desired.

## Adding custom type annotations

If you want to add your new/custom type annotations to `anci`, see `src/anci/handlers` for now or, alternatively, open an issue. Documentation on adding your own custom annotations will be added soon.

## Other CLI frameworks

- [`argparse`](https://docs.python.org/3/library/argparse.html) - Base of `anci` and reliable for small scripts but very verbose otherwise.
- [`click`](https://github.com/pallets/click) - Too. Many. Decorators. Not much else to say.
- [`typer`](https://github.com/fastapi/typer) - Mature ecosystem, "type-aware" but doesn't fully take advantage of type annotations (for example, see `typer`'s use of `Annotated`).
