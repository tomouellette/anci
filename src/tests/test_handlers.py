import inspect
import argparse
import pytest

from typing import Annotated, get_args
from anci.typing import Path, Gt, Ge, Lt, Le, Interval, MaxLen, MinLen, Len

from anci.handlers._type import (
    FloatHandler,
    IntHandler,
    StrHandler,
    BoolHandler,
    BytesHandler,
    PathHandler,
    ListHandler,
    TupleHandler,
    SetHandler
)

from anci.handlers._annotated import (
    GreaterThanHandler,
    GreaterEqualHandler,
    LessThanHandler,
    LessEqualHandler,
    IntervalHandler,
    LenHandler
)


def get_type_params(func: callable):
    params = inspect.signature(func).parameters
    name, parameter = list(params.items())[0]
    return name, parameter.annotation


def get_annotated_params(func: callable):
    params = inspect.signature(func).parameters
    name, parameter = list(params.items())[0]
    annotated_type, metadata = get_args(parameter.annotation)
    return name, annotated_type, metadata


def check_type_handler(value, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", **kwargs)
    if value is None:
        return parser.parse_args(["--test"]).test
    return parser.parse_args(["--test", value]).test


def check_container_handler(*values, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", **kwargs)
    return parser.parse_args(["--test", *values]).test


class TestTypeHandlers:
    def test_float(self):
        def _func(x: float):
            return x

        kwargs = FloatHandler().build(*get_type_params(_func))
        assert check_type_handler("0.123", **kwargs) == 0.123, \
            "FloatTypeHandler failed."

        with pytest.raises(SystemExit):
            check_type_handler("A", **kwargs)

    def test_int(self):
        def _func(x: int):
            return x

        kwargs = IntHandler().build(*get_type_params(_func))
        assert check_type_handler("123", **kwargs) == 123, \
            "IntTypeHandler failed."

        with pytest.raises(SystemExit):
            check_type_handler("A", **kwargs)

    def test_str(self):
        def _func(x: str):
            return x

        kwargs = StrHandler().build(*get_type_params(_func))
        assert check_type_handler("123", **kwargs) == "123", \
            "StrTypeHandler failed."

    def test_bool(self):
        def _func(x: bool):
            return x

        for t in ["True", "T", "yes", "1"]:
            kwargs = BoolHandler().build(*get_type_params(_func))
            assert check_type_handler(t, **kwargs), \
                "BoolTypeHandler (no default, true) failed."

        for f in ["False", "F", "no", "0"]:
            kwargs = BoolHandler().build(*get_type_params(_func))
            assert not check_type_handler(f, **kwargs), \
                "BoolTypeHandler (no default, false) failed."

        with pytest.raises(SystemExit):
            check_type_handler("A", **kwargs)

    def test_bytes(self):
        def _func(x: int):
            return x

        kwargs = BytesHandler().build(*get_type_params(_func))
        assert check_type_handler("123", **kwargs) == b"123", \
            "BytesTypeHandler failed."

    def test_path(self):
        def _func(x: Path):
            return x

        kwargs = PathHandler().build(*get_type_params(_func))
        path = check_type_handler("test_handlers.py", **kwargs)
        assert isinstance(path, Path), "PathTypeHandler failed."


class TestContainerHandlers:
    def test_list(self):
        for type_ in [int, float, str]:
            def _func(x: list[type_]):
                return x

            arg = "1 2 3"
            out = [type_(i) for i in arg.split()]

            kwargs = ListHandler().build(*get_type_params(_func))
            result = check_container_handler(*arg.split(), **kwargs)
            assert isinstance(result, list)
            assert isinstance(result[0], type_)
            assert result == out

    def test_tuple(self):
        for type_ in [int, float, str]:
            def _func(x: tuple[type_]):
                return x

            arg = "1 2 3"
            out = tuple([type_(i) for i in arg.split()])

            kwargs = TupleHandler().build(*get_type_params(_func))
            result = check_container_handler(*arg.split(), **kwargs)
            assert isinstance(result, tuple)
            assert isinstance(result[0], type_)
            assert result == out

    def test_set(self):
        def _func(x: set[int]):
            return x

        kwargs = SetHandler().build(*get_type_params(_func))
        result = check_container_handler(*"1 2 3".split(), **kwargs)
        assert isinstance(result, set)
        assert 1 in result
        assert result == {1, 2, 3}


class TestAnnotatedHandlers:
    def test_inequality_scalar(self):
        for type_ in (int, float):
            inequalities = [
                (GreaterThanHandler, Gt(10), 11, 10),
                (GreaterEqualHandler, Ge(10), 10, 9),
                (LessThanHandler, Lt(10), 9, 10),
                (LessEqualHandler, Le(10), 10, 11),
            ]

            for (handler, inequality, success, failure) in inequalities:
                def _func(x: Annotated[type_, inequality]):
                    return x

                kwargs = handler().build(*get_annotated_params(_func))
                assert check_type_handler(str(success), **kwargs) == success, \
                    f"{handler.__name__} {type_.__name__} failure."

                with pytest.raises(SystemExit):
                    check_type_handler(str(failure), **kwargs)

    def test_inequality_container(self):
        for container in (list, tuple, set):
            for type_ in (int, float):
                inequalities = [
                    (GreaterThanHandler, Gt(10), [11, 12], [10, 11]),
                    (GreaterEqualHandler, Ge(10), [10, 11], [9, 10]),
                    (LessThanHandler, Lt(10), [8, 9], [9, 10]),
                    (LessEqualHandler, Le(10), [9, 10], [10, 11]),
                ]

                for (handler, inequality, success, failure) in inequalities:
                    success_str = " ".join(map(str, success))
                    failure_str = " ".join(map(str, failure))

                    success = container(success)
                    failure = container(failure)

                    def _func(x: Annotated[container[type_], inequality]):
                        return x

                    kwargs = handler().build(*get_annotated_params(_func))
                    assert check_container_handler(
                        *success_str.split(), **kwargs) == success, \
                        f"{handler.__name__} list[{type.__name}] failure."

                    with pytest.raises(argparse.ArgumentTypeError):
                        check_container_handler(*failure_str.split(), **kwargs)

    def test_inequality_invalid(self):
        for handler, inequality in [
            (GreaterThanHandler, Gt),
            (GreaterEqualHandler, Ge),
            (LessThanHandler, Lt),
            (LessEqualHandler, Le)
        ]:
            def _func(x: Annotated[str, inequality(10)]):
                return x

            with pytest.raises(TypeError):
                handler().build(*get_annotated_params(_func))

    def test_interval_scalar(self):
        for type_ in (int, float):
            def _func(x: Annotated[type_, Interval(ge=10, le=20)]):
                return x

            kwargs = IntervalHandler().build(*get_annotated_params(_func))
            assert check_type_handler("15", **kwargs) == 15, \
                f"IntervalHandler {type_.__name__} failure."

            with pytest.raises(SystemExit):
                check_type_handler("9", **kwargs)

    def test_interval_container(self):
        for container in (list, tuple, set):
            for type_ in (int, float):
                success = [10, 20]
                failure = [9, 21]

                success_str = " ".join(map(str, success))
                failure_str = " ".join(map(str, failure))

                success = container(success)
                failure = container(failure)

                def _func(x: Annotated[container[type_], Interval(ge=10, le=20)]):
                    return x

                kwargs = IntervalHandler().build(*get_annotated_params(_func))
                assert check_container_handler(
                    *success_str.split(), **kwargs) == success, \
                    f"IntervalHandler list[{type_.__name__}] failure."

                with pytest.raises(argparse.ArgumentTypeError):
                    check_container_handler(*failure_str.split(), **kwargs)

    def test_len_str(self):
        for handler, success, failure in [
            (MaxLen(3), "abc", "abcd"),
            (MinLen(3), "abc", "ab"),
            (Len(min_length=3, max_length=3), "abc", "abcd")
        ]:
            def _func(x: Annotated[str, handler]):
                return x

            kwargs = LenHandler().build(*get_annotated_params(_func))
            assert check_type_handler(success, **kwargs) == success, \
                f"{handler.__name__} str failure."

            with pytest.raises(SystemExit):
                check_type_handler(failure, **kwargs)

    def test_len_container(self):
        for container in (list, tuple, set):
            for type_ in (int, float):
                for handler, success, failure in [
                    (MaxLen(3), [1, 2, 3], [1, 2, 3, 4]),
                    (MinLen(3), [1, 2, 3], [1, 2]),
                    (Len(min_length=3, max_length=3), [1, 2, 3], [1, 2])
                ]:
                    success_str = " ".join(map(str, success))
                    failure_str = " ".join(map(str, failure))

                    success = container(success)
                    failure = container(failure)

                    def _func(x: Annotated[container[type_], handler]):
                        return x

                    kwargs = LenHandler().build(*get_annotated_params(_func))
                    assert check_container_handler(
                        *success_str.split(), **kwargs) == success, \
                        f"{handler.__name__} {
                            container.__name__}[{type_.__name__}] failure."

                    with pytest.raises(SystemExit):
                        check_container_handler(*failure_str.split(), **kwargs)
