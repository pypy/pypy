"""
PyPy-specific typing support for PEP 695 (Type Parameter Syntax).

This module provides TypeVar, ParamSpec, TypeVarTuple, TypeAliasType and Generic
implementations with support for lazy evaluation of bounds, constraints,
and type alias values.

These are moved here from typing.py to mirror CPython's approach where
these classes are implemented in C.

This module is intended as a hacky replacement for the relevant parts of typing.py
that were rewritten in C in the CPython support for PEP 695, to allow us to start
implementing PEP 695 support in PyPy without having to rewrite large parts of
the typing module in RPython.
A lot of this code must be rewritten in RPython later to establish proper
parity with CPython's implementation around introspection, immutability, etc.
"""

__all__ = [
    'TypeVar', 'ParamSpec', 'TypeVarTuple', 'TypeAliasType',
    'ParamSpecArgs', 'ParamSpecKwargs', 'Generic',
]


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


class _BoundVarianceMixin:
    """Mixin giving __init__ bound and variance arguments.

    This is used by TypeVar and ParamSpec, which both employ the notions of
    a type 'bound' (restricting type arguments to be a subtype of some
    specified type) and type 'variance' (determining subtype relations between
    generic types).
    """
    def __init__(self, bound, covariant, contravariant, infer_variance):
        """Used to setup TypeVars and ParamSpec's bound, covariant,
        contravariant and infer_variance attributes.
        """
        if covariant and contravariant:
            raise ValueError("Bivariant types are not supported.")
        self.__covariant__ = bool(covariant)
        self.__contravariant__ = bool(contravariant)
        self.__infer_variance__ = bool(infer_variance)
        if bound:
            from typing import _type_check
            self.__bound__ = _type_check(bound, "Bound must be a type.")
        else:
            self.__bound__ = None

    def __or__(self, right):
        import typing
        return typing._make_union(self, right)

    def __ror__(self, left):
        import typing
        return typing._make_union(left, self)

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


class _LazyEvaluator:
    __slots__ = ('_name',)

    def __set_name__(self, owner, name):
        assert name.startswith("__") and name.endswith("__")
        self._name = name[2:-2]

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = getattr(instance, f"__evaluate_{self._name}__")()
        setattr(instance, f"__{self._name}__", value)
        return value


class TypeVar(_Immutable, _PickleUsingNameMixin, _BoundVarianceMixin):
    """Type variable with support for lazy bound/constraints evaluation.

    Usage::

      T = TypeVar('T')  # Can be anything
      A = TypeVar('A', str, bytes)  # Must be str or bytes

    Type variables exist primarily for the benefit of static type
    checkers.  They serve as the parameters for generic types as well
    as for generic function definitions.
    """

    def __init__(self, name, *constraints, bound=None, covariant=False,
                 contravariant=False, infer_variance=False):
        self.__name__ = name
        super().__init__(bound, covariant, contravariant, infer_variance)
        if constraints:
            if len(constraints) == 1:
                raise TypeError("A single constraint is not allowed")
            if bound is not None:
                raise TypeError("Constraints cannot be combined with bound=...")
            from typing import _type_check
            msg = "TypeVar(name, constraint, ...): constraints must be types."
            self.__constraints__ = tuple(_type_check(t, msg) for t in constraints)
        else:
            self.__constraints__ = ()

        # TODO: Fix __module__

    __bound__ = _LazyEvaluator()
    __constraints__ = _LazyEvaluator()

    def __typing_subst__(self, arg):
        """Used for generic type substitution."""
        import typing
        return typing._typevar_subst(self, arg)

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of TypeVar")


class ParamSpec(_Immutable, _PickleUsingNameMixin, _BoundVarianceMixin):
    """Parameter specification variable.

    The preferred way to construct a parameter specification is via the
    dedicated syntax for generic functions, classes, and type aliases,
    where the use of '**' creates a parameter specification::

        type IntFunc[**P] = Callable[P, int]

    For compatibility with Python 3.11 and earlier, ParamSpec objects
    can also be created as follows::

        P = ParamSpec('P')

    Parameter specification variables exist primarily for the benefit of
    static type checkers.  They are used to forward the parameter types of
    one callable to another callable, a pattern commonly found in
    higher-order functions and decorators.  They are only valid when used
    in ``Concatenate``, or as the first argument to ``Callable``, or as
    parameters for user-defined Generics. See class Generic for more
    information on generic types.

    An example for annotating a decorator::

        def add_logging[**P, T](f: Callable[P, T]) -> Callable[P, T]:
            '''A type-safe decorator to add logging to a function.'''
            def inner(*args: P.args, **kwargs: P.kwargs) -> T:
                logging.info(f'{f.__name__} was called')
                return f(*args, **kwargs)
            return inner

        @add_logging
        def add_two(x: float, y: float) -> float:
            '''Add two numbers together.'''
            return x + y

    Parameter specification variables can be introspected. e.g.::

        >>> P = ParamSpec("P")
        >>> P.__name__
        'P'

    Note that only parameter specification variables defined in the global
    scope can be pickled.
    """

    def __init__(self, name, *, bound=None, covariant=False, contravariant=False, infer_variance=False):
        self.__name__ = name
        super().__init__(bound, covariant, contravariant, infer_variance)

        # TODO: __module__ is automatically set by Python to the defining module

        # Create args and kwargs attributes
        self.args = ParamSpecArgs(self)
        self.kwargs = ParamSpecKwargs(self)

    def __typing_subst__(self, arg):
        import typing
        return typing._paramspec_subst(self, arg)

    def __typing_prepare_subst__(self, alias, args):
        import typing
        return typing._paramspec_prepare_subst(self, alias, args)

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of ParamSpec")


class ParamSpecArgs:
    """The args for a ParamSpec object.

    Given P = ParamSpec('P'), P.args is an instance of ParamSpecArgs.
    """
    __slots__ = ('__origin__',)

    def __init__(self, origin):
        self.__origin__ = origin

    def __repr__(self):
        return f"{self.__origin__.__name__}.args"

    def __hash__(self):
        return hash((self.__origin__, "args"))

    def __eq__(self, other):
        if isinstance(other, ParamSpecArgs):
            return self.__origin__ == other.__origin__
        return NotImplemented

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of ParamSpecArgs")


class ParamSpecKwargs:
    """The kwargs for a ParamSpec object.

    Given P = ParamSpec('P'), P.kwargs is an instance of ParamSpecKwargs.
    """
    __slots__ = ('__origin__',)

    def __init__(self, origin):
        self.__origin__ = origin

    def __repr__(self):
        return f"{self.__origin__.__name__}.kwargs"

    def __hash__(self):
        return hash((self.__origin__, "kwargs"))

    def __eq__(self, other):
        if isinstance(other, ParamSpecKwargs):
            return self.__origin__ == other.__origin__
        return NotImplemented

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of ParamSpecKwargs")


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

    def __repr__(self):
        return self.__name__

    def __iter__(self):
        from typing import Unpack
        yield Unpack[self]

    def __typing_subst__(self, arg):
        raise TypeError("Substitution of bare TypeVarTuple is not supported")

    def __typing_prepare_subst__(self, alias, args):
        import typing
        return typing._typevartuple_prepare_subst(self, alias, args)

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of TypeVarTuple")


class TypeAliasType(_PickleUsingNameMixin):
    """Runtime representation of a type alias created with PEP 695 syntax.

    The __value__ is lazily evaluated - the evaluate_func is called
    only when __value__ is first accessed, then cached.

    Example::

        type Point = tuple[float, float]
        # Point is a TypeAliasType with __name__ = 'Point'
        # and __value__ = tuple[float, float]
    """

    def __init__(self, name, value, *, type_params=()):
        """Initialize a TypeAliasType.

        Args:
            name: The name of the type alias.
            value: The value of the type alias.
            type_params: The type parameters of the alias (for generic aliases).
        """
        self._name = name
        self._type_params = tuple(type_params) if type_params else ()
        self.__value__ = value
        # __module__ is automatically set by Python to the defining module

    @property
    def __name__(self):
        return self._name

    @property
    def __type_params__(self):
        return self._type_params

    @property
    def __parameters__(self):
        """Return the type parameters, unpacking any TypeVarTuples."""
        if not self._type_params:
            return ()
        result = []
        for param in self._type_params:
            if isinstance(param, TypeVarTuple):
                result.extend(param)
            else:
                result.append(param)
        return tuple(result)

    __value__ = _LazyEvaluator()

    def __repr__(self):
        return self._name

    def __getitem__(self, parameters):
        """Support generic type alias subscripting: Alias[T]."""
        if not self._type_params:
            raise TypeError("Only generic type aliases are subscriptable")
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


# Factory functions for the compiler
# These are called from generated bytecode to create type parameters
# with lazy evaluation support.

def _make_typevar(name):
    return TypeVar(name, infer_variance=True)


def _make_typevar_with_bound(name, evaluate_bound):
    t = TypeVar(name, infer_variance=True)
    del t.__bound__
    t.__evaluate_bound__ = evaluate_bound
    return t


def _make_typevar_with_constraints(name, evaluate_constraints):
    t = TypeVar(name, infer_variance=True)
    del t.__constraints__
    t.__evaluate_constraints__ = evaluate_constraints
    return t


def _make_paramspec(name):
    return ParamSpec(name, infer_variance=True)


def _make_typevartuple(name):
    return TypeVarTuple(name)


def _make_typealiastype(name, evaluate_value, type_params):
    t = TypeAliasType(name, None, type_params=type_params)
    del t.__value__
    t.__evaluate_value__ = evaluate_value
    return t


class Generic:
    """Abstract base class for generic types.

    A generic type is typically declared by inheriting from
    this class parameterized with one or more type variables.
    For example, a generic mapping type might be defined as::

      class Mapping(Generic[KT, VT]):
          def __getitem__(self, key: KT) -> VT:
              ...
          # Etc.

    This class can then be used as follows::

      def lookup_name(mapping: Mapping[KT, VT], key: KT, default: VT) -> VT:
          try:
              return mapping[key]
          except KeyError:
              return default
    """
    __slots__ = ()
    _is_protocol = False

    def __class_getitem__(cls, params):
        import typing
        return typing._generic_class_getitem(cls, params)

    def __init_subclass__(cls, *args, **kwargs):
        import typing
        return typing._generic_init_subclass(cls, *args, **kwargs)
