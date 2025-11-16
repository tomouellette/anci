# Copyright (c) 2025, Tom Ouellette
# Licensed under the MIT License

import argparse


class LengthConstrainedList(argparse.Action):
    """An argparse action enforcing minimum and/or maximum length constraints.

    Parameters
    ----------
    min_len : int
        Minimum number of elements required in the list. If ``None``, no lower
        bound is enforced.
    max_len : int
        Maximum number of elements allowed in the list. If ``None``, no upper
        bound is enforced.
    **kwargs
        Additional keyword arguments passed to `argparse.Action`.

    Raises
    ------
    argparse.ArgumentError
        If the provided list has fewer than `min_len` or more than `max_len`
        elements.

    Examples
    --------
    >>> parser = argparse.ArgumentParser()
    >>> parser.add_argument(
    ...     "--items",
    ...     nargs="+",
    ...     action=LengthConstrainedList,
    ...     min_len=2,
    ...     max_len=5
    ... )
    """

    def __init__(self, min_len: int = None, max_len: int = None, **kwargs):
        self.min_len = min_len
        self.max_len = max_len
        super().__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if self.min_len is not None and len(values) < self.min_len:
            raise argparse.ArgumentError(
                self, f"List must have at least {self.min_len} elements"
            )
        if self.max_len is not None and len(values) > self.max_len:
            raise argparse.ArgumentError(
                self, f"List must have at most {self.max_len} elements"
            )
        setattr(namespace, self.dest, values)


class ContainerCastAction(argparse.Action):
    """An argparse action that casts each container element to a given type.

    Parameters
    ----------
    container_type : type
        The container class to use for the final value (e.g., `list`, `set`,
        `tuple`).
    cast : callable
        A function or type that converts each element from its string
        representation to the desired type.
    **kwargs
        Additional keyword arguments passed to `argparse.Action`.

    Examples
    --------
    >>> parser = argparse.ArgumentParser()
    >>> parser.add_argument(
    ...     "--numbers",
    ...     nargs="+",
    ...     action=ContainerCastAction,
    ...     container_type=list,
    ...     cast=int
    ... )
    """

    def __init__(self, container_type, cast, **kwargs):
        self.container_type = container_type
        self.cast = cast
        super().__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # Note: Cast each element, then convert to target container type
        casted = [self.cast(v) for v in values]
        setattr(namespace, self.dest, self.container_type(casted))


class ConstrainedContainerAction(argparse.Action):
    """An argparse action that casts elements to a given type, wraps them in a
    container, and optionally validates both length constraints and custom
    validation rules.

    Parameters
    ----------
    container_type : type
        The container class to use for the final value (e.g., `list`, `set`,
        `tuple`).
    cast : callable
        A function or type that converts each element from its string
        representation to the desired type.
    validate : callable
        A function that takes the casted container and raises an exception if
        it is invalid. If ``None``, no additional validation is performed.
    min_len : int
        Minimum number of elements required. If ``None``, no lower bound is
        enforced.
    max_len : int
        Maximum number of elements allowed. If ``None``, no upper bound is
        enforced.
    **kwargs
        Additional keyword arguments passed to `argparse.Action`.

    Raises
    ------
    argparse.ArgumentError
        If the container has fewer than `min_len` or more than `max_len`
        elements.
    Exception
        Any exception raised by the `validate` function.

    Examples
    --------
    >>> def check_positive(values):
    ...     if any(v <= 0 for v in values):
    ...         raise ValueError("All values must be positive.")

    >>> parser = argparse.ArgumentParser()
    >>> parser.add_argument(
    ...     "--scores",
    ...     nargs="+",
    ...     action=ConstrainedContainerAction,
    ...     container_type=list,
    ...     cast=int,
    ...     validate=check_positive,
    ...     min_len=1
    ... )
    """

    def __init__(
        self, container_type, cast, validate=None, min_len=None, max_len=None, **kwargs
    ):
        self.container_type = container_type
        self.cast = cast
        self.validate = validate
        self.min_len = min_len
        self.max_len = max_len
        super().__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if self.min_len is not None and len(values) < self.min_len:
            raise argparse.ArgumentError(
                self, f"Expected at least {self.min_len} elements, got {len(values)}"
            )

        if self.max_len is not None and len(values) > self.max_len:
            raise argparse.ArgumentError(
                self, f"Expected at most {self.max_len} elements, got {len(values)}"
            )

        casted = [self.cast(v) for v in values]
        if self.validate:
            self.validate(casted)

        setattr(namespace, self.dest, self.container_type(casted))
