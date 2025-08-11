# Copyright (c) 2025, Tom Ouellette
# Licensed under the MIT License

from typing import TypeVar, List, Tuple, Set

from annotated_types import (
    Gt,
    Ge,
    Lt,
    Le,
    Interval,
    MaxLen,
    MinLen,
    Len,
)

T = TypeVar("T")

Container = list[T] | set[T] | tuple[T, ...] | List[T] | Tuple[T] | Set[T]

AnnotatedType = Gt | Ge | Lt | Le | Interval | MaxLen | MinLen | Len
