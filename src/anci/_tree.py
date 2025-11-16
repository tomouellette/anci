# Copyright (c) 2025, Tom Ouellette
# Licensed under the MIT License

import sys
import inspect
import argparse

from collections import defaultdict
from typing import Callable

from ._arg import is_anci_arg
from .handlers import get_kwargs

COMMAND_TREE = defaultdict(dict)


def cmd(*names: str) -> Callable:
    """Decorator to register functions as specific command-line subcommands.

    This decorator allows you to expose a Python function as a command-line
    subcommand, nested under a specified path. When the decorated function
    is called from the command line, its logic will execute.

    Parameters
    ----------
    *names : str
        One or more strings that define the hierarchical path to the subcommand.
        Each string represents a segment in the command path. For example,
        `@cmd("network", "configure")` registers a command accessible via
        `[program] network configure`.

    Returns
    -------
    Callable
        The decorated function, after it has been registered within the
        command tree.

    Raises
    ------
    ValueError
        If the decorator is used without parentheses on a function directly
        (e.g., `@cmd def my_command(): ...`). This usage is reserved for
        `@base` commands, which serve as containers for subcommands.

    See Also
    --------
    base : Decorator for registering base commands that only show help.
    register_command : Function responsible for adding the command to the tree.

    Examples
    --------
    Registering a nested subcommand:

    >>> @cmd("files", "delete", "temp")
    ... def delete_temp_files(path: str):
    ...     '''Deletes temporary files from the specified path.'''
    ...     print(f"Deleting temp files from: {path}")

    This would register the `delete_temp_files` function as a command
    accessible through a CLI structure like `[program] files delete temp`.
    """

    def decorator(func):
        if callable(names[0]) if names else False:
            raise ValueError(
                "A single (@command('..') or no command name (@command) "
                + "was provided. This indicates this command is a @base "
                + "command. Please decorate with @base('..') instead."
            )

            # Deprecated: Handle @command without args (top-level command)
            # This is deprecated as parent commands are decorated with base.
            # actual_func = names[0]
            # register_command([], actual_func)
            # return actual_func
        else:
            # Note: Register commands of arbitrary number while enforcing
            # presence of parent commands e.g @command("one", "two", "three")
            register_command(list(names), func)
            return func

    # Note: If used without parentheses on a function directly
    if len(names) == 1 and callable(names[0]):
        func = names[0]
        register_command([], func)
        return func

    return decorator


class MissingBaseCommandError(Exception):
    """Raised when a nested command is missing a parent base command.

    Notes
    -----
    For example, if you decorate a function with @command("two", "red") but do
    not have a @base("two") decorated function then an error will be thrown. We
    implement this error to enforce proper command-line hierarchies.
    """

    pass


def base(*names) -> Callable:
    """Decorator to register base command that only shows help for subcommands.

    A base command is a special type of command that, when invoked, does not
    execute any specific logic but instead displays help information for its
    available subcommands. This is useful for grouping related commands under
    a common namespace.

    Parameters
    ----------
    *names : str or Callable
        If `path` consists of strings, they represent the path segments for the
        base command. For example, `@base("group", "subgroup")` registers
        a base command at `group subgroup`.
        If `path` contains a single callable argument, it's assumed the decorator
        is used without parentheses, e.g., `@base def my_base_cmd(): ...`.
        In this case, the base command is registered at the top level.

    Returns
    -------
    Callable
        The decorated function, or a decorator function if called with path arguments.

    Raises
    ------
    TypeError
        If the decorator is used incorrectly, e.g., with non-string path arguments
        when parentheses are used.

    Examples
    --------
    Registering a base command with a path:

    >>> @base("two", "ops")
    ... def two_ops_base():
    ...     '''Base command for two operations.'''
    ...     pass

    Registering a top-level base command (without parentheses):

    >>> @base
    ... def top_level_base():
    ...     '''Top-level base command.'''
    ...     pass
    """

    def decorator(func):
        register_base_command(list(names), func)
        return func

    # Note: If used without parentheses on a function directly
    if len(names) == 1 and callable(names[0]):
        func = names[0]
        register_base_command([], func)
        return func

    return decorator


def register_base_command(names: list[str], func: Callable) -> Callable:
    """Register a base command that only shows help.

    This function traverses the `COMMAND_TREE` (a global or module-level dict)
    based on the provided `path` and marks the specified function `func` as a
    base command. A base command serves as a container for subcommands and when
    executed, displays help for those subcommands rather than executing any an
    logic itself.

    Parameters
    ----------
    names : list[str]
        A list of string segments representing the hierarchical path to where
        the base command should be registered within the `COMMAND_TREE`. An
        empty list `[]` indicates a top-level base command.
    func : Callable
        The Python function to be registered as the base command. This function
        is typically a placeholder that does not perform any operation itself.

    Returns
    -------
    Callable
        The input function `func`, after it has been registered.

    See Also
    --------
    base : The decorator that uses this function for registering base commands.

    Notes
    -----
    This function changes the global `COMMAND_TREE` in place. The `_base_func`,
    `_name`, and `_is_base` keys are added to the corresponding node in the
    `COMMAND_TREE` to mark and identify the base command.
    """
    current = COMMAND_TREE
    for segment in names:
        if "_subcommands" not in current:
            current["_subcommands"] = defaultdict(dict)
        current = current["_subcommands"][segment]

    current["_base_func"] = func
    current["_name"] = func.__name__
    current["_is_base"] = True

    def decorator(func):
        if callable(names[0]) if names else False:
            # Note: Handle @command without parentheses (top-level command)
            actual_func = names[0]
            register_command([], actual_func)
            return actual_func
        else:
            # Note: Handle @command("path", "to", "cmd")
            register_command(list(names), func)
            return func

    # Note: If used without parentheses on a function directly
    if len(names) == 1 and callable(names[0]):
        func = names[0]
        register_command([], func)
        return func

    return decorator


def register_command(names: list[str], func: Callable) -> None:
    """Register a command function at the given path in the command tree.

    This function adds a command to a global command tree structure. It first
    validates that all parent paths have a corresponding base command defined
    and then traverses the tree to place the function at the correct location.

    Parameters
    ----------
    path : list[str]
        A list of string segments representing the hierarchical path to the
        command. An empty list signifies a top-level command.
    func : Callable
        The Python function to be registered as a command.

    Raises
    ------
    MissingBaseCommandError
        If a parent path in the hierarchy does not have a corresponding
        base command registered.

    Notes
    -----
    This function modifies the global `COMMAND_TREE` in place. The function
    is stored under the `_func` key, and the function's name under `_name`.
    """
    validate_parent_commands(names)

    current = COMMAND_TREE
    for segment in names:
        if "_subcommands" not in current:
            current["_subcommands"] = defaultdict(dict)
        current = current["_subcommands"][segment]
    current["_func"] = func
    current["_name"] = func.__name__


def validate_parent_commands(names: list[str]) -> None:
    """Validate that all parent paths have base commands defined.

    This is a helper function used by `register_command` to ensure that
    commands are only registered under existing base commands or at the
    top level. It iterates through the command path and checks each
    parent node in the `COMMAND_TREE` for the presence of a base function.

    Parameters
    ----------
    path : list[str]
        The full hierarchical path of the command to be validated.

    Raises
    ------
    MissingBaseCommandError
        If any parent segment in the path does not have a base command
        (`_base_func`) or a regular command (`_func`) defined, indicating
        a missing parent structure.
    """
    for i in range(len(names)):
        parent_path = names[:i]
        if not parent_path:
            continue

        current = COMMAND_TREE
        for segment in parent_path:
            if "_subcommands" not in current:
                raise MissingBaseCommandError(
                    f"Missing base command for {' -> '.join(parent_path)}. "
                    + f"You must define a @base{tuple(parent_path)} command "
                    + "before defining nested commands."
                )

            current = current["_subcommands"][segment]

        # Note: Check if this parent path has either a base or regular command
        if "_base_func" not in current and "_func" not in current:
            raise MissingBaseCommandError(
                f"Missing base command for {' -> '.join(parent_path)}. "
                + f"You must define a @base{tuple(parent_path)} command "
                + "before defining nested commands."
            )


def add_subparser(subparser: argparse.ArgumentParser, func: Callable) -> None:
    """Convert function with `anci.Arg` annotations into argparse arguments.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        The subparser to which arguments will be added.
    func : Callable
        A function whose parameters are annotated with ``anci.Arg``.
    """
    sig = inspect.signature(func)

    for name, param in sig.parameters.items():
        if not is_anci_arg(param.annotation):
            raise TypeError(
                f"Parameter '{name}' of '{func.__name__}' "
                "must be annotated with `anci.Arg[type, help]`."
            )

        ann = param.annotation
        arg_type = ann.__type_hint__
        help_text = ann.__help_text__

        kwargs = get_kwargs(name, arg_type)
        kwargs["help"] = help_text or None
        kwargs["required"] = param.default is inspect.Parameter.empty

        if param.default is not inspect.Parameter.empty:
            kwargs["default"] = param.default
            if help_text:
                end = "." if help_text.endswith(".") else ""
                kwargs["help"] = f"{help_text.rstrip('.')} (default: %(default)s){end}"

        subparser.add_argument(f"--{name}", **kwargs)


def register_recursive(
    subparsers: argparse._SubParsersAction,
    command_tree: dict,
    names: list[str] = [],
    formatter_class=None,
) -> None:
    """Recursively register all commands and subcommands with subparsers.

    This is the core function for building the full command-line parser
    structure. It traverses the `command_tree` dictionary and creates
    `argparse` subparsers for each command, base command, or command group,
    linking them to their corresponding functions.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        The subparser action object to which new subparsers are added.
    command_tree : dict
        A dictionary representing the current level of the command hierarchy.
    path : list[str]
        The current path of the command hierarchy being processed.
    formatter_class : Any
        An `argparse` formatter class to use for help messages. If not
        provided, the default formatter is used.

    See Also
    --------
    register : The main entry point for registering all commands.
    add_subparser : Function used to add arguments for each command.
    """
    for name, subtree in command_tree.items():
        if name == "_subcommands":
            continue

        current_names = names + [name]

        # Note: Check if this node has a regular function/command
        if "_func" in subtree:
            func = subtree["_func"]
            parser_kwargs = {"description": func.__doc__}
            if formatter_class:
                parser_kwargs["formatter_class"] = formatter_class
            sub = subparsers.add_parser(name, **parser_kwargs)
            sub.set_defaults(func=func, command_path=current_names, is_base=False)
            add_subparser(sub, func)
            sub.set_defaults(func=func, command_path=current_names)

            # Note: If this command also has subcommands, add them
            if "_subcommands" in subtree:
                sub_subparsers = sub.add_subparsers(
                    dest=f"subcmd_{'_'.join(current_names)}",
                    metavar="<subcommand>",
                    help="Subcommands",
                )
                register_recursive(
                    sub_subparsers,
                    subtree["_subcommands"],
                    current_names,
                    formatter_class,
                )

        # Note; Check if this node has a base function
        elif "_base_func" in subtree:
            func = subtree["_base_func"]
            parser_kwargs = {"description": func.__doc__}
            if formatter_class:
                parser_kwargs["formatter_class"] = formatter_class
            sub = subparsers.add_parser(name, **parser_kwargs)

            # Note: Base commands don't take arguments, they just show help
            def base_command_handler(subparser):
                def handler():
                    subparser.print_help()
                    sys.exit(0)

                return handler

            sub.set_defaults(
                func=base_command_handler(sub), command_path=current_names, is_base=True
            )

            # Note: Base commands must have subcommands
            if "_subcommands" in subtree:
                sub_subparsers = sub.add_subparsers(
                    dest=f"subcmd_{'_'.join(current_names)}",
                    metavar="<subcommand>",
                    help="Subcommands",
                )
                register_recursive(
                    sub_subparsers,
                    subtree["_subcommands"],
                    current_names,
                    formatter_class,
                )

        # Note: If this is just a command group, create parser for subcommands
        elif "_subcommands" in subtree:
            parser_kwargs = {"help": f"Commands under {name}"}
            if formatter_class:
                parser_kwargs["formatter_class"] = formatter_class
            sub = subparsers.add_parser(name, **parser_kwargs)
            sub_subparsers = sub.add_subparsers(
                dest=f"subcmd_{'_'.join(current_names)}",
                metavar="<subcommand>",
                help="Subcommands",
            )
            register_recursive(
                sub_subparsers, subtree["_subcommands"], current_names, formatter_class
            )


def register(subparsers: argparse._SubParsersAction, formatter_class=None) -> None:
    """Register all commands with the argument parser.

    This function handles both top-level commands and commands nested under
    '_subcommands'. It ensures all commands appear in the help text properly.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        The main subparser action object from `argparse`.
    formatter_class : Any
        An `argparse` formatter class to use for help messages.
    """

    def register_command(subparsers_obj, name, details, command_path):
        """Helper to register a single command."""

        if "_func" in details:
            # Note: Regular command with function
            func = details["_func"]
            help_text = func.__doc__ or f"Execute {name} command"

            parser_kwargs = {"help": help_text, "description": func.__doc__}
            if formatter_class:
                parser_kwargs["formatter_class"] = formatter_class

            sub = subparsers_obj.add_parser(name, **parser_kwargs)
            add_subparser(sub, func)
            sub.set_defaults(
                func=func, command_path=command_path + [name], is_base=False
            )

            # Note: Handle nested subcommands
            if "_subcommands" in details:
                nested_subparsers = sub.add_subparsers(
                    dest=f"subcmd_{'_'.join(command_path + [name])}",
                    metavar="<subcommand>",
                    help="Available subcommands",
                )
                register_commands_from_dict(
                    nested_subparsers, details["_subcommands"], command_path + [name]
                )

        elif "_base_func" in details:
            # Note: Base command (shows help when called without subcommands)
            func = details["_base_func"]
            help_text = func.__doc__ or f"Base command for {name}"

            parser_kwargs = {"help": help_text}
            if formatter_class:
                parser_kwargs["formatter_class"] = formatter_class

            sub = subparsers_obj.add_parser(name, **parser_kwargs)

            # Note: Base commands show help when called
            def base_command_handler(subparser):
                def handler():
                    subparser.print_help()
                    sys.exit(0)

                return handler

            sub.set_defaults(
                func=base_command_handler(sub),
                command_path=command_path + [name],
                is_base=True,
            )

            # Note: Handle nested subcommands for base commands
            if "_subcommands" in details:
                nested_subparsers = sub.add_subparsers(
                    dest=f"subcmd_{'_'.join(command_path + [name])}",
                    metavar="<subcommand>",
                    help="Available subcommands",
                )
                register_commands_from_dict(
                    nested_subparsers, details["_subcommands"], command_path + [name]
                )

    def register_commands_from_dict(subparsers_obj, commands_dict, command_path):
        """Register all commands from a dictionary."""
        for name, details in commands_dict.items():
            if name.startswith("_"):
                continue
            register_command(subparsers_obj, name, details, command_path)

    # Note: Check if we have any top-level commands (not starting with '_')
    top_level_commands = {
        name: details
        for name, details in COMMAND_TREE.items()
        if not name.startswith("_")
    }

    if top_level_commands:
        # Note: We have top-level commands, register them
        register_commands_from_dict(subparsers, top_level_commands, [])

    # Note: Handle commands nested under '_subcommands'
    if "_subcommands" in COMMAND_TREE:
        if not top_level_commands:
            # Note: All commands are under _subcommands, register at top level
            register_commands_from_dict(subparsers, COMMAND_TREE["_subcommands"], [])
        else:
            # Note: We have both top-level and nested commands.Register nested
            # ones using the existing recursive function
            register_recursive(
                subparsers, COMMAND_TREE["_subcommands"], [], formatter_class
            )


def find_selected_function(args: argparse.Namespace) -> Callable | None:
    """Find which command function was selected based on parsed arguments.

    This is a utility function that checks the parsed `argparse` object
    for the `func` attribute, which is set by the `argparse` subparser.
    This attribute holds the callable function to be executed.

    Parameters
    ----------
    args : argparse.Namespace
        The namespace object returned by `parser.parse_args()`.

    Returns
    -------
    Callable or None
        The selected command function if found, otherwise `None`.
    """
    if hasattr(args, "func"):
        return args.func

    return None


def runner(args: argparse.Namespace, parser: argparse.ArgumentParser):
    """Run the selected command with the parsed arguments.

    This function is the main execution loop for the command-line interface.
    It retrieves the selected function from the `args` object, prepares the
    arguments by removing argparse-specific keys, and then calls the function.
    It also handles cases where no command is selected or when a base command
    is invoked (which should print help and exit).

    Parameters
    ----------
    args : argparse.Namespace
        The namespace object containing the parsed command-line arguments.
    parser : argparse.ArgumentParser
        The main argument parser instance, used for printing help messages.

    Returns
    -------
    Any
        The return value of the executed command function.

    Raises
    ------
    SystemExit
        If no command is selected or if a base command is invoked.
    """
    if not hasattr(args, "command") or args.command is None:
        parser.print_help()
        sys.exit(0)

    func = find_selected_function(args)
    if func is None:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, "is_base") and args.is_base:
        func()
        return

    func_args = vars(args).copy()

    keys_to_remove = ["func", "command", "command_path", "is_base"]
    keys_to_remove.extend([k for k in func_args.keys() if k.startswith("subcmd_")])

    for key in keys_to_remove:
        func_args.pop(key, None)

    func(**func_args)
