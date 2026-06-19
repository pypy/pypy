"""_typing: re-export PyPy's typing primitives so that lib-python/3/typing.py
finds the same TypeVar/ParamSpec/Generic classes that PyPy's PEP 695 runtime
uses when creating type parameters from the 'class Foo[T]' syntax.

If _typing and _pypy_typing exposed different TypeVar classes, isinstance
checks in typing._is_typevar_like would fail for PEP 695 type variables.
"""
from _pypy_typing import (   # noqa: F401
    TypeVar,
    ParamSpec,
    TypeVarTuple,
    ParamSpecArgs,
    ParamSpecKwargs,
    TypeAliasType,
    Generic,
)


def _idfunc(_, x):
    return x
