# Copyright (c) 2025, Tom Ouellette
# Licensed under the MIT License

import argparse

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Tuple, Set, get_args, get_origin

from anci._action import ContainerCastAction
from anci._types import Container

TYPE_HANDLERS: dict[type, dict[str, Any]] = {}


def register_type(*types):
    """Decorator to register a type handler for one or more Python types.

    Parameters
    ----------
    *types : type
        One or more Python types (e.g., `int`, `str`, `list`) to associate
        with the decorated handler class.

    Returns
    -------
    callable
        A decorator that registers the class in the `TYPE_HANDLERS` registry.
    """

    def decorator(cls):
        for t in types:
            TYPE_HANDLERS[t] = cls
        return cls

    return decorator


class BaseTypeHandler(ABC):
    """Abstract base class for all type handlers.

    Type handlers are responsible for converting and validating command-line
    arguments for specific Python types, producing keyword arguments compatible
    with `argparse.ArgumentParser.add_argument`.
    """

    @abstractmethod
    def build(self, name: str, annotated_type: type) -> dict[str, Any]:
        """Build an argparse configuration for a parameter.

        Parameters
        ----------
        name : str
            The command-line argument name.
        annotated_type : type
            The base type annotation parsed from function signature.

        Returns
        -------
        dict[str, Any]
            Keyword arguments for `ArgumentParser.add_argument`.

        Raises
        ------
        NotImplementedError
            If the subclass does not implement this method.
        """
        pass


@register_type(float)
class FloatHandler(BaseTypeHandler):
    """Handler for `float` command-line arguments."""

    cast = staticmethod(float)

    def build(self, name: str, annotated_type: float) -> dict[str, Any]:
        return {"type": float}


@register_type(int)
class IntHandler(BaseTypeHandler):
    """Handler for `int` command-line arguments."""

    cast = staticmethod(int)

    def build(self, name: str, annotated_type: int) -> dict[str, Any]:
        return {"type": int}


@register_type(str)
class StrHandler(BaseTypeHandler):
    """Handler for `str` command-line arguments."""

    cast = staticmethod(str)

    def build(self, name: str, annotated_type: str) -> dict[str, Any]:
        return {"type": str}


@register_type(bool)
class BoolHandler(BaseTypeHandler):
    """Handler for `bool` command-line arguments.

    Supports both flag-style booleans (when a default is given) and
    explicit true/false value parsing (when no default is given).
    """

    def build(self, name: str, annotated_type: bool) -> dict[str, Any]:
        def str_to_bool(v):
            if isinstance(v, bool):
                return v
            if v.lower() in ("true", "t", "yes", "1"):
                return True
            elif v.lower() in ("false", "f", "no", "0"):
                return False
            raise argparse.ArgumentTypeError(f"invalid boolean value: {v}.")

        return {"type": str_to_bool}


@register_type(bytes)
class BytesHandler(BaseTypeHandler):
    """Handler for `bytes` command-line arguments.

    Converts strings from the command-line into UTF-8 encoded bytes.
    """

    def build(self, name: str, annotated_type: bytes) -> dict[str, Any]:
        def to_bytes(v: str) -> bytes:
            return v.encode("utf-8")

        return {"type": to_bytes}


@register_type(Path)
class PathHandler(BaseTypeHandler):
    """Handler for `pathlib.Path` command-line arguments."""

    cast = staticmethod(Path)

    def build(self, name: str, annotated_type: Path) -> dict[str, Any]:
        return {"type": self.cast}


class BaseContainerHandler(BaseTypeHandler):
    """Base handler for container-type command-line arguments.

    This class provides validation and configuration for arguments that
    represent typed containers, such as `list[int]`, `tuple[str, ...]`, or
    `set[float]`. It ensures the container is homogeneous, the element type
    is registered, and returns the appropriate `argparse` settings.
    """

    container_type = list

    def build(self, name: str, annotated_type: Container) -> dict[str, Any]:
        """Build an argparse configuration for a typed container parameter.

        Parameters
        ----------
        name : str
            The command-line argument name.
        annotated_type : type
            Type of container and container elements.

        dict
            Keyword arguments for `ArgumentParser.add_argument`, including
            the `nargs`, `cast` function, container type, and a custom
            container action.

        Raises
        ------
        TypeError
            If the parameter annotation is missing an element type,
            does not match the expected container type, is not homogeneous,
            or has an unregistered element type.
        """
        args = get_args(annotated_type)

        if not args:
            raise TypeError(
                f"{self.container_type.__name__} argument '{name}' must specify "
                f"an element type (e.g., {self.container_type.__name__}[int])."
            )

        if get_origin(annotated_type) is not self.container_type:
            raise TypeError(
                f"Container type for {name} must be {self.container_type.__name__}."
            )

        element_type = args[0]
        for e in args:
            if e is not element_type and e is not Ellipsis:
                raise TypeError(
                    f"{self.container_type.__name__} argument '{name}' must have "
                    f"homogeneous elements: {annotated_type}"
                )

        if element_type not in TYPE_HANDLERS:
            raise TypeError(
                f"No registered handler for {self.container_type.__name__} "
                f"element type: {element_type}"
            )

        element_handler = TYPE_HANDLERS[element_type]

        return {
            "nargs": "+",
            "cast": element_handler.cast,
            "container_type": self.container_type,
            "action": ContainerCastAction,
        }


@register_type(list, List)
class ListHandler(BaseContainerHandler):
    """Handler for `list` command-line arguments.

    Enforces that the argument is a typed `list` with a registered
    element type. Supports homogeneous lists only.
    """

    container_type = list


@register_type(tuple, Tuple)
class TupleHandler(BaseContainerHandler):
    """Handler for `tuple` command-line arguments.

    Enforces that the argument is a typed `tuple` with a registered
    element type. Supports homogeneous tuples or ellipsis notation for
    variable length tuples.
    """

    container_type = tuple


@register_type(set, Set)
class SetHandler(BaseContainerHandler):
    """Handler for `set` command-line arguments.

    Enforces that the argument is a typed `set` with a registered
    element type. Supports homogeneous sets only.
    """

    container_type = set
