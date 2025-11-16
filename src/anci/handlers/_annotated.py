# Copyright (c) 2025, Tom Ouellette
# Licensed under the MIT License

import argparse
import operator

from abc import ABC, abstractmethod
from annotated_types import Gt, Ge, Lt, Le, Interval, MaxLen, MinLen, Len
from typing import Annotated, List, Tuple, Set, Any, get_args, get_origin

from anci._action import ConstrainedContainerAction
from anci._types import Container

ANNOTATED_HANDLERS: dict[type, dict[str, Any]] = {}


def register_annotated(*meta_types):
    """Register an `AnnotatedTypeHandler` class for one or more metadata types.

    Parameters
    ----------
    *meta_types : type
        Metadata types from `annotated_types` (e.g., `Gt`, `Interval`) that
        the decorated handler class should process.

    Returns
    -------
    callable
        A decorator that registers the handler class.
    """

    def wrapper(cls):
        for m in meta_types:
            ANNOTATED_HANDLERS[m] = cls
        return cls

    return wrapper


class AnnotatedTypeHandler(ABC):
    """Abstract base class for all annotated type handlers.

    Subclasses must implement the `build` method, which maps an annotated
    type and its metadata to an `argparse` argument configuration dictionary.
    """

    @abstractmethod
    def build(
        self, name: str, annotated_type: Annotated[type, ...], metadata: Any
    ) -> dict[str, Any]:
        """Build an `argparse` argument config from annotated type metadata.

        Parameters
        ----------
        name : str
            Name of the argument (for error messages).
        annotated_type : type
            The underlying type from the `Annotated` declaration.
        metadata : object
            The metadata instance from `annotated_types`.

        Returns
        -------
        dict of str to Any
            Keyword arguments to pass to `ArgumentParser.add_argument`.
        """
        pass


class InequalityHandler(AnnotatedTypeHandler):
    """Base handler for numeric inequality constraints.

    Attributes
    ----------
    metadata_attr : str
        Name of the metadata attribute (e.g., `"gt"`, `"le"`) containing the
        threshold value.
    op_func : callable
        Comparison function from the `operator` module (e.g., `operator.gt`).
    op_symbol : str
        String representation of the operator for error messages.
    """

    metadata_attr: str
    op_func: callable
    op_symbol: str

    def build(
        self,
        name: str,
        annotated_type: Container[int] | Container[float] | int | float,
        metadata: Gt | Ge | Lt | Le,
    ) -> dict[str, Any]:
        """Create an argparse configuration enforcing an inequality constraint.

        Parameters
        ----------
        name : str
            Argument name.
        annotated_type : type
            Base type or container type (list, tuple, set) of int or float.
        metadata : Gt | Ge | Lt | Le
            Inequality metadata instance.

        Returns
        -------
        dict
            Configuration for `add_argument`.
        """
        threshold = getattr(metadata, self.metadata_attr)
        origin = get_origin(annotated_type)

        if origin in (list, tuple, set, List, Tuple, Set):
            element_type = get_args(annotated_type)[0]

            if element_type not in (int, float):
                raise TypeError(
                    f"Invalid `Annotated` metadata for {name}. "
                    f"`{type(metadata).__name__}` is only valid with "
                    "`int` or `float` elements."
                )

            def validate_container(values):
                casted = []
                for v in values:
                    v_cast = element_type(v)
                    if not self.op_func(v_cast, threshold):
                        raise argparse.ArgumentTypeError(
                            f"Each element of {name} must be {self.op_symbol} "
                            f"{threshold}, got {v}"
                        )
                    casted.append(v_cast)
                return origin(casted) if origin is not list else casted

            return {
                "nargs": "+",
                "type": element_type,
                "action": ConstrainedContainerAction,
                "container_type": origin,
                "cast": element_type,
                "validate": validate_container,
            }

        if annotated_type not in (int, float):
            raise TypeError(
                f"Invalid `Annotated` metadata for {name}. "
                f"`{type(metadata).__name__}` is only valid with "
                "`int` or `float`."
            )

        def validate_scalar(value):
            value = annotated_type(value)
            if not self.op_func(value, threshold):
                raise argparse.ArgumentTypeError(
                    f"{name} must be {self.op_symbol} {threshold}, got {value}"
                )
            return value

        return {"type": validate_scalar}


@register_annotated(Gt)
class GreaterThanHandler(InequalityHandler):
    """Handler for `Gt` metadata."""

    metadata_attr = "gt"
    op_func = staticmethod(operator.gt)
    op_symbol = ">"


@register_annotated(Ge)
class GreaterEqualHandler(InequalityHandler):
    """Handler for `Ge` metadata."""

    metadata_attr = "ge"
    op_func = staticmethod(operator.ge)
    op_symbol = ">="


@register_annotated(Lt)
class LessThanHandler(InequalityHandler):
    """Handler for `Lt` metadata."""

    metadata_attr = "lt"
    op_func = staticmethod(operator.lt)
    op_symbol = "<"


@register_annotated(Le)
class LessEqualHandler(InequalityHandler):
    """Handler for `Le` metadata."""

    metadata_attr = "le"
    op_func = staticmethod(operator.le)
    op_symbol = "<="


@register_annotated(Interval)
class IntervalHandler(AnnotatedTypeHandler):
    """Handler for `Interval` metadata.

    Supports inclusive and exclusive bounds, with optional lower and upper
    limits. Works for scalar values or containers of int/float.
    """

    def build(
        self,
        name: str,
        annotated_type: Container[int] | Container[float] | int | float,
        metadata: Interval,
    ) -> dict[str, Any]:
        """Build an argparse config for a numeric interval constraint.

        Parameters
        ----------
        name : str
            Argument name.
        annotated_type : type
            Base type or container type (list, tuple, set) of int or float.
        metadata : Interval
            Interval metadata instance.

        Returns
        -------
        dict
            Configuration for `add_argument`.
        """
        gt = getattr(metadata, "gt", None)
        ge = getattr(metadata, "ge", None)
        lt = getattr(metadata, "lt", None)
        le = getattr(metadata, "le", None)

        if gt is not None and ge is not None:
            raise TypeError("Interval cannot have both 'gt' and 'ge' specified.")
        if lt is not None and le is not None:
            raise TypeError("Interval cannot have both 'lt' and 'le' specified.")

        lower = gt if gt is not None else ge
        lower_inclusive = ge is not None or gt is None
        upper = lt if lt is not None else le
        upper_inclusive = le is not None or lt is None

        origin = get_origin(annotated_type)

        if origin in (list, tuple, set, List, Tuple, Set):
            element_type = get_args(annotated_type)[0]
            if element_type not in (int, float):
                raise TypeError(
                    f"Invalid `Annotated` metadata for {name}. "
                    "Interval is only valid for numeric element types."
                )

            def validate_container(values):
                casted = []
                for v in values:
                    v_cast = element_type(v)
                    if lower is not None:
                        if lower_inclusive and v_cast < lower:
                            raise argparse.ArgumentTypeError(
                                f"Each element of {name} must be ≥ {lower}"
                            )
                        elif not lower_inclusive and v_cast <= lower:
                            raise argparse.ArgumentTypeError(
                                f"Each element of {name} must be > {lower}"
                            )
                    if upper is not None:
                        if upper_inclusive and v_cast > upper:
                            raise argparse.ArgumentTypeError(
                                f"Each element of {name} must be ≤ {upper}"
                            )
                        elif not upper_inclusive and v_cast >= upper:
                            raise argparse.ArgumentTypeError(
                                f"Each element of {name} must be < {upper}"
                            )
                    casted.append(v_cast)

                if origin is tuple:
                    return tuple(casted)
                elif origin is set:
                    return set(casted)
                return casted

            return {
                "nargs": "+",
                "type": element_type,
                "action": ConstrainedContainerAction,
                "container_type": origin if origin is not list else list,
                "cast": element_type,
                "validate": validate_container,
            }

        if annotated_type not in (int, float):
            raise TypeError(
                f"Invalid `Annotated` metadata for {name}. "
                "Interval is only valid with int or float."
            )

        def validate_scalar(value):
            value = annotated_type(value)

            if lower is not None:
                if lower_inclusive and value < lower:
                    raise argparse.ArgumentTypeError(f"Value must be ≥ {lower}")
                elif not lower_inclusive and value <= lower:
                    raise argparse.ArgumentTypeError(f"Value must be > {lower}")

            if upper is not None:
                if upper_inclusive and value > upper:
                    raise argparse.ArgumentTypeError(f"Value must be ≤ {upper}")
                elif not upper_inclusive and value >= upper:
                    raise argparse.ArgumentTypeError(f"Value must be < {upper}")

            return value

        return {"type": validate_scalar}


@register_annotated(MaxLen, MinLen, Len)
class LenHandler:
    """Handler for sequence length constraints.

    Supports `MaxLen`, `MinLen`, and `Len` metadata from ``annotated_types``.
    Can be applied to containers (list, tuple, set) or strings/bytes. For
    containers, this handler sets up a custom argparse action that enforces
    minimum/maximum element counts. For strings and bytes, it validates length
    at parse time.
    """

    def build(
        self,
        name: str,
        annotated_type: Container[Any] | str,
        metadata: MaxLen | MinLen | Len,
    ) -> dict[str, Any]:
        origin = get_origin(annotated_type)
        args = get_args(annotated_type)

        if origin in (list, tuple, set, List, Tuple, Set):
            elem_type = args[0] if args else str

            return {
                "nargs": "+",
                "action": ConstrainedContainerAction,
                "container_type": origin,
                "cast": elem_type,
                "min_len": getattr(metadata, "min_length", None),
                "max_len": getattr(metadata, "max_length", None),
            }

        if annotated_type in (str, bytes):

            def validator(value):
                if hasattr(metadata, "length") and len(value) != metadata.length:
                    raise argparse.ArgumentTypeError(
                        f"Argument '{name}' must have exactly "
                        f"{metadata.length} characters"
                    )
                if hasattr(metadata, "min_length") and len(value) < metadata.min_length:
                    raise argparse.ArgumentTypeError(
                        f"Argument '{name}' must have at least "
                        f"{metadata.min_length} characters"
                    )
                if hasattr(metadata, "max_length") and len(value) > metadata.max_length:
                    raise argparse.ArgumentTypeError(
                        f"Argument '{name}' must have at most "
                        f"{metadata.max_length} characters"
                    )
                return value

            return {"type": validator}

        raise TypeError(
            f"Invalid `Annotated` metadata for '{name}'. "
            "`MaxLen`, `MinLen`, or `Len` can only be used with "
            "list, tuple, set, or string types."
        )
