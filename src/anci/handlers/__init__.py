from typing import Annotated, get_origin, get_args

from anci._types import Container, AnnotatedType

from ._annotated import ANNOTATED_HANDLERS
from ._type import TYPE_HANDLERS


def get_kwargs(name: str, arg_type: type | Container | AnnotatedType) -> dict:
    """
    Build argparse keyword arguments for a given parameter.

    Parameters
    ----------
    name : str
        Argument name.
    arg_type : type | Container | AnnotatedType
        A valid base type, container type, or annotated type parsed from
        an anci.Arg annotation.

    Returns
    -------
    dict
        Keyword arguments to be passed to argparse's add_argument().

    Raises
    ------
    TypeError
        If no suitable handler is registered.
    """
    origin = get_origin(arg_type)

    if origin is Annotated:
        base_type, *metadata = get_args(arg_type)
        for meta in metadata:
            if handler_cls := ANNOTATED_HANDLERS.get(type(meta)):
                return handler_cls().build(name, base_type, meta)

    handler_cls = TYPE_HANDLERS.get(arg_type) or TYPE_HANDLERS.get(origin)
    if handler_cls:
        return handler_cls().build(name, arg_type)

    raise TypeError(f"No registered handler for type: {arg_type!r}")
