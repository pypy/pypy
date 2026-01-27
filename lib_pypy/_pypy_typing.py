"""
PyPy-specific typing support for PEP 695 (Type Parameter Syntax).

This module provides TypeVar, ParamSpec, TypeVarTuple, and TypeAliasType
implementations with support for lazy evaluation of bounds, constraints,
and type alias values.

These are moved here from typing.py to mirror CPython's approach where
these classes are implemented in C.
"""

__all__ = [
    'TypeVar', 'ParamSpec', 'TypeVarTuple', 'TypeAliasType',
    '_make_typevar', '_make_typevar_with_bound', '_make_typevar_with_constraints',
    '_make_paramspec', '_make_typevartuple',
]

# Sentinel for lazy evaluation - internal use only
_LAZY_EVALUATION_SENTINEL = object()


def _caller(depth=2):
    """Get the module name of the caller at the specified depth."""
    import sys
    try:
        return sys._getframe(depth).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        return None


class _Immutable:
    """Mixin that makes instances immutable (no __dict__)."""
    __slots__ = ()

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class _PickleUsingNameMixin:
    """Mixin for types that can be pickled using their __name__."""

    def __reduce__(self):
        return self.__name__


class TypeVar(_Immutable, _PickleUsingNameMixin):
    """Type variable with support for lazy bound/constraints evaluation.

    Usage::

      T = TypeVar('T')  # Can be anything
      A = TypeVar('A', str, bytes)  # Must be str or bytes

    Type variables exist primarily for the benefit of static type
    checkers.  They serve as the parameters for generic types as well
    as for generic function definitions.
    """

    __slots__ = ('__name__', '__covariant__', '__contravariant__',
                 '__infer_variance__', '_bound', '_constraints',
                 '__evaluate_bound__', '__evaluate_constraints__')

    def __init__(self, name, *constraints, bound=None, covariant=False,
                 contravariant=False, infer_variance=False):
        self.__name__ = name
        self.__covariant__ = covariant
        self.__contravariant__ = contravariant
        self.__infer_variance__ = infer_variance

        # Handle lazy evaluation sentinel for bound
        self.__evaluate_bound__ = None
        if bound is not None and isinstance(bound, tuple) and len(bound) == 2:
            if bound[0] is _LAZY_EVALUATION_SENTINEL:
                self.__evaluate_bound__ = bound[1]
                self._bound = None
            else:
                self._bound = bound
        else:
            self._bound = bound

        # Handle lazy evaluation sentinel for constraints
        self.__evaluate_constraints__ = None
        if constraints and constraints[0] is _LAZY_EVALUATION_SENTINEL:
            self.__evaluate_constraints__ = constraints[1]
            self._constraints = ()
        else:
            if len(constraints) == 1:
                raise TypeError("A single constraint is not allowed")
            self._constraints = constraints

        # Used for pickling
        # __module__ is automatically set by Python to the defining module

    @property
    def __bound__(self):
        """Return the bound, evaluating lazily if needed."""
        if self.__evaluate_bound__ is not None:
            self._bound = self.__evaluate_bound__()
            self.__evaluate_bound__ = None  # Cache result
        return self._bound

    @property
    def __constraints__(self):
        """Return the constraints, evaluating lazily if needed."""
        if self.__evaluate_constraints__ is not None:
            self._constraints = self.__evaluate_constraints__()
            self.__evaluate_constraints__ = None  # Cache result
        return self._constraints

    def has_default(self):
        """Return False - PEP 696 defaults not implemented yet."""
        return False

    def __repr__(self):
        if self.__infer_variance__:
            prefix = ''
        elif self.__covariant__:
            prefix = '+'
        elif self.__contravariant__:
            prefix = '-'
        else:
            prefix = '~'
        return prefix + self.__name__

    def __hash__(self):
        return hash((self.__name__,))

    def __eq__(self, other):
        # TypeVars are only equal if they are the same object
        return self is other

    def __or__(self, other):
        from typing import Union
        return Union[self, other]

    def __ror__(self, other):
        from typing import Union
        return Union[other, self]

    def __typing_subst__(self, arg):
        """Used for generic type substitution."""
        return arg

    def __reduce__(self):
        return self.__name__


class ParamSpec(_Immutable, _PickleUsingNameMixin):
    """Parameter specification variable.

    Usage::

      P = ParamSpec('P')

    Parameter specification variables exist primarily for the benefit of
    static type checkers. They are used to specify the type parameters
    of generic callables.
    """

    __slots__ = ('__name__', '__covariant__', '__contravariant__',
                 '__infer_variance__', 'args', 'kwargs')

    def __init__(self, name, *, covariant=False, contravariant=False,
                 infer_variance=False):
        self.__name__ = name
        self.__covariant__ = covariant
        self.__contravariant__ = contravariant
        self.__infer_variance__ = infer_variance
        # __module__ is automatically set by Python to the defining module

        # Create args and kwargs attributes
        self.args = _ParamSpecArgs(self)
        self.kwargs = _ParamSpecKwargs(self)

    @property
    def __bound__(self):
        return None

    @property
    def __constraints__(self):
        return ()

    def has_default(self):
        return False

    def __repr__(self):
        if self.__infer_variance__:
            prefix = ''
        elif self.__covariant__:
            prefix = '+'
        elif self.__contravariant__:
            prefix = '-'
        else:
            prefix = '~'
        return prefix + self.__name__

    def __hash__(self):
        return hash((self.__name__,))

    def __eq__(self, other):
        return self is other

    def __or__(self, other):
        from typing import Union
        return Union[self, other]

    def __ror__(self, other):
        from typing import Union
        return Union[other, self]

    def __reduce__(self):
        return self.__name__


class _ParamSpecArgs:
    """The args for a ParamSpec object.

    Given P = ParamSpec('P'), P.args is an instance of _ParamSpecArgs.
    """
    __slots__ = ('__origin__',)

    def __init__(self, origin):
        self.__origin__ = origin

    def __repr__(self):
        return f"{self.__origin__.__name__}.args"

    def __hash__(self):
        return hash((self.__origin__, "args"))

    def __eq__(self, other):
        if isinstance(other, _ParamSpecArgs):
            return self.__origin__ == other.__origin__
        return NotImplemented


class _ParamSpecKwargs:
    """The kwargs for a ParamSpec object.

    Given P = ParamSpec('P'), P.kwargs is an instance of _ParamSpecKwargs.
    """
    __slots__ = ('__origin__',)

    def __init__(self, origin):
        self.__origin__ = origin

    def __repr__(self):
        return f"{self.__origin__.__name__}.kwargs"

    def __hash__(self):
        return hash((self.__origin__, "kwargs"))

    def __eq__(self, other):
        if isinstance(other, _ParamSpecKwargs):
            return self.__origin__ == other.__origin__
        return NotImplemented


class TypeVarTuple(_Immutable, _PickleUsingNameMixin):
    """Type variable tuple.

    Usage::

      Ts = TypeVarTuple('Ts')

    A TypeVarTuple is a placeholder for an *arbitrary* number of types.
    """

    __slots__ = ('__name__',)

    def __init__(self, name):
        self.__name__ = name
        # __module__ is automatically set by Python to the defining module

    def has_default(self):
        return False

    def __repr__(self):
        return self.__name__

    def __hash__(self):
        return hash((self.__name__,))

    def __eq__(self, other):
        return self is other

    def __iter__(self):
        from typing import Unpack
        yield Unpack[self]

    def __reduce__(self):
        return self.__name__


class TypeAliasType:
    """Runtime representation of a type alias created with PEP 695 syntax.

    The __value__ is lazily evaluated - the evaluate_func is called
    only when __value__ is first accessed, then cached.

    Example::

        type Point = tuple[float, float]
        # Point is a TypeAliasType with __name__ = 'Point'
        # and __value__ = tuple[float, float]
    """

    __slots__ = ('_name', '_type_params', '_evaluate', '_value', '_evaluated')

    def __init__(self, name, evaluate_func, *, type_params=()):
        """Initialize a TypeAliasType.

        Args:
            name: The name of the type alias.
            evaluate_func: A callable that returns the type alias value when called.
            type_params: The type parameters of the alias (for generic aliases).
        """
        self._name = name
        self._type_params = tuple(type_params) if type_params else ()
        self._evaluate = evaluate_func
        self._value = None
        self._evaluated = False
        # __module__ is automatically set by Python to the defining module

    @property
    def __name__(self):
        """Return the name of the type alias."""
        return self._name

    @property
    def __type_params__(self):
        """Return the type parameters of the type alias."""
        return self._type_params

    @property
    def __value__(self):
        """Lazily evaluate and return the type alias value."""
        if not self._evaluated:
            self._value = self._evaluate()
            self._evaluated = True
        return self._value

    def __repr__(self):
        return self._name

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        # TypeAliasTypes are only equal if they are the same object
        return self is other

    def __getitem__(self, parameters):
        """Support generic type alias subscripting: Alias[T]."""
        from typing import _GenericAlias
        if not isinstance(parameters, tuple):
            parameters = (parameters,)
        return _GenericAlias(self, parameters)

    def __or__(self, other):
        """Support | for Union types."""
        from typing import Union
        return Union[self, other]

    def __ror__(self, other):
        """Support | for Union types (reverse)."""
        from typing import Union
        return Union[other, self]

    def __reduce__(self):
        return self._name


# Factory functions for the compiler
# These are called from generated bytecode to create type parameters
# with lazy evaluation support.

def _make_typevar(name, *, covariant=False, contravariant=False,
                  infer_variance=False):
    """Create a TypeVar without bound or constraints."""
    return TypeVar(name, covariant=covariant, contravariant=contravariant,
                   infer_variance=infer_variance)


def _make_typevar_with_bound(name, evaluate_bound, *, covariant=False,
                             contravariant=False, infer_variance=False):
    """Create a TypeVar with lazy bound evaluation.

    Args:
        name: The name of the TypeVar.
        evaluate_bound: A callable that returns the bound when called.
    """
    return TypeVar(name, bound=(_LAZY_EVALUATION_SENTINEL, evaluate_bound),
                   covariant=covariant, contravariant=contravariant,
                   infer_variance=infer_variance)


def _make_typevar_with_constraints(name, evaluate_constraints, *, covariant=False,
                                   contravariant=False, infer_variance=False):
    """Create a TypeVar with lazy constraints evaluation.

    Args:
        name: The name of the TypeVar.
        evaluate_constraints: A callable that returns a tuple of constraints.
    """
    return TypeVar(name, _LAZY_EVALUATION_SENTINEL, evaluate_constraints,
                   covariant=covariant, contravariant=contravariant,
                   infer_variance=infer_variance)


def _make_paramspec(name, *, covariant=False, contravariant=False,
                    infer_variance=False):
    """Create a ParamSpec."""
    return ParamSpec(name, covariant=covariant, contravariant=contravariant,
                     infer_variance=infer_variance)


def _make_typevartuple(name):
    """Create a TypeVarTuple."""
    return TypeVarTuple(name)
