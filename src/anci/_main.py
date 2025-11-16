# Copyright (c) 2025, Tom Ouellette
# Licensed under the MIT License

import argparse
from typing import Any, Type

from ._tree import register, runner


def main(
    prog: str | None = None,
    usage: str | None = None,
    description: str | None = None,
    epilog: str | None = None,
    formatter_class: Type[argparse.HelpFormatter] = argparse.HelpFormatter,
    prefix_chars: str = "-",
    fromfile_prefix_chars: str | None = None,
    argument_default: Any = None,
    conflict_handler: str = "error",
    add_help: bool = True,
    allow_abbrev: bool = True,
    exit_on_error: bool = True,
) -> Any:
    """Initializes and runs a command-line interface using argparse.

    This function serves as the primary entry point for a command-line
    application. It constructs an `argparse.ArgumentParser` object with the
    provided parameters, registers all available commands, and then parses
    and executes the command based on user input.

    Parameters
    ----------
    prog : str
        Name of the program.
    usage : str
        A string describing the program usage.
    description : str
        Text to display before the argument help.
    epilog : str
        Text to display after the argument help.
    formatter_class : type
        A class for customizing the help output.
        `argparse.HelpFormatter`.
    prefix_chars : str
        The set of characters that prefix optional arguments.
    fromfile_prefix_chars : str
        The set of characters that prefix files from which additional arguments
        should be read.
    argument_default : Any
        The global default value for arguments.
    conflict_handler : str
        The strategy for resolving conflicting optional arguments. Defaults
        to `'error'`.
    add_help : bool
        If `True`, adds a `-h/--help` option to the parser.
    allow_abbrev : bool
        If `True`, allows long options to be abbreviated if the abbreviation
        is unambiguous.
    exit_on_error : bool
        If `True`, determines whether the parser exits with error info
        when an error occurs.

    Returns
    -------
    Any
        The return value of the executed command function, if any.
        Otherwise, it returns `None`.

    References
    --------
    .. [1] `argparse`: https://docs.python.org/3/library/argparse.html

    Notes
    -----
    This function relies on a global command tree structure and helper
    functions like `register` and `runner` to define and execute commands.
    It is designed to be called once as the entry point of the application.
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        usage=usage,
        description=description,
        epilog=epilog,
        formatter_class=formatter_class,
        prefix_chars=prefix_chars,
        fromfile_prefix_chars=fromfile_prefix_chars,
        argument_default=argument_default,
        conflict_handler=conflict_handler,
        add_help=add_help,
        allow_abbrev=allow_abbrev,
        exit_on_error=exit_on_error,
    )

    subparsers = parser.add_subparsers(
        dest="command", metavar="<command>", help="Available commands", required=True
    )

    register(subparsers, formatter_class=formatter_class)
    runner(parser.parse_args(), parser)
