# Copyright (c) 2025, Tom Ouellette
# Licensed under the MIT License

from typing import _AnnotatedAlias, Any
from ._types import AnnotatedType


class Arg:
    """Type annotation for command-line arguments with help text.

    Raises
    ------
    TypeError
        If Arg[...] contains more than 2 parameters. Or, if a single parameter
        is provided, it is not a valid base type or typing.Annotated type.
    TypeError
        If a second parameter is provided and it is not a help text string.

    Examples
    --------
    Annotating function arguments:

    >>> Arg[int]                      # no help
    >>> Arg[int, "Help text here"]    # with help
    """

    def __class_getitem__(cls, params: tuple[type, str] | type | AnnotatedType):
        # Note: This is the entry point for performing the initial checks on
        # function type annotations before building the _registry.COMMAND_TREE.
        # Any new arguments types need to be added here if necessary. There is
        # current support for base types, containers, and a subset of range and
        # length checks via annotated_types.
        if isinstance(params, tuple) and len(params) == 2:
            type_hint, help_text = params
        elif isinstance(params, (type, _AnnotatedAlias)):
            type_hint, help_text = params, ""
        else:
            raise TypeError(
                "Arg[...] takes 1 parameter (type) or 2 parameters (type and help text)"
            )

        if not isinstance(help_text, str):
            raise TypeError("Help text must be a string.")

        return type(
            "ArgType",
            (),
            {
                "__type_hint__": type_hint,
                "__help_text__": help_text,
                "__origin__": cls,
                "__args__": (type_hint, help_text),
            },
        )


def is_anci_arg(annotation: Any) -> bool:
    """Check if a function annotation is an anci.Arg"""
    return hasattr(annotation, "__origin__") and annotation.__origin__ is Arg
