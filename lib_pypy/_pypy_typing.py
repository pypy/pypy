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


def _caller_module():
    import sys
    try:
        return sys._getframe(2).f_globals.get('__name__')
    except (AttributeError, ValueError):
        return None


def _attr_guard(*, readonly=(), not_writable=(), strict=False):
    """Class decorator that adds __setattr__/__delattr__ for attribute protection.

    Args:
        readonly: attrs giving "readonly attribute" (matches C READONLY members)
        not_writable: attrs giving "attribute 'X' of ... not writable" (matches C getset)
        strict: if True, reject ALL unknown attribute setting/deletion
    """
    readonly = frozenset(readonly)
    not_writable = frozenset(not_writable)

    def _check(self, name):
        if name in readonly:
            raise AttributeError('readonly attribute')
        if name in not_writable:
            raise AttributeError(
                f"attribute '{name}' of 'typing.{type(self).__name__}' "
                f"objects is not writable"
            )
        if strict:
            raise AttributeError(
                f"'typing.{type(self).__name__}' object has no attribute '{name}'"
            )

    def decorator(cls):
        def __setattr__(self, name, value):
            _check(self, name)
            object.__setattr__(self, name, value)

        def __delattr__(self, name):
            _check(self, name)
            object.__delattr__(self, name)

        cls.__setattr__ = __setattr__
        cls.__delattr__ = __delattr__
        return cls

    return decorator


class _Immutable:
    """Mixin that makes instances immutable."""

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
        if infer_variance and (covariant or contravariant):
            raise ValueError("Variance cannot be specified with infer_variance.")
        object.__setattr__(self, '__covariant__', bool(covariant))
        object.__setattr__(self, '__contravariant__', bool(contravariant))
        object.__setattr__(self, '__infer_variance__', bool(infer_variance))
        if bound:
            from typing import _type_check
            object.__setattr__(self, '__bound__',
                               _type_check(bound, "Bound must be a type."))
        else:
            object.__setattr__(self, '__bound__', None)

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
        object.__setattr__(instance, f"__{self._name}__", value)
        return value


@_attr_guard(
    readonly={'__name__', '__covariant__', '__contravariant__', '__infer_variance__'},
    not_writable={'__bound__', '__constraints__'},
)
class TypeVar(_Immutable, _PickleUsingNameMixin, _BoundVarianceMixin):
    """Type variable.

    The preferred way to construct a type variable is via the dedicated
    syntax for generic functions, classes, and type aliases::

        class Sequence[T]:  # T is a TypeVar
            ...

    This syntax can also be used to create bound and constrained type
    variables::

        # S is a TypeVar bound to str
        class StrSequence[S: str]:
            ...

        # A is a TypeVar constrained to str or bytes
        class StrOrBytesSequence[A: (str, bytes)]:
            ...

    However, if desired, reusable type variables can also be constructed
    manually, like so::

       T = TypeVar('T')  # Can be anything
       S = TypeVar('S', bound=str)  # Can be any subtype of str
       A = TypeVar('A', str, bytes)  # Must be exactly str or bytes

    Type variables exist primarily for the benefit of static type
    checkers.  They serve as the parameters for generic types as well
    as for generic function and type alias definitions.

    The variance of type variables is inferred by type checkers when they
    are created using the type parameter syntax and when
    ``infer_variance=True`` is passed. Manually created type variables may
    be explicitly marked covariant or contravariant by passing
    ``covariant=True`` or ``contravariant=True``. By default, manually
    created type variables are invariant. See PEP 484 and PEP 695 for more
    details.

    """

    def __init__(self, name, *constraints, bound=None, covariant=False,
                 contravariant=False, infer_variance=False):
        object.__setattr__(self, '__name__', name)
        super().__init__(bound, covariant, contravariant, infer_variance)
        if constraints:
            if len(constraints) == 1:
                raise TypeError("A single constraint is not allowed")
            if bound is not None:
                raise TypeError("Constraints cannot be combined with bound=...")
            from typing import _type_check
            msg = "TypeVar(name, constraint, ...): constraints must be types."
            object.__setattr__(self, '__constraints__',
                               tuple(_type_check(t, msg) for t in constraints))
        else:
            object.__setattr__(self, '__constraints__', ())
        object.__setattr__(self, '__module__', _caller_module())

    __bound__ = _LazyEvaluator()
    __constraints__ = _LazyEvaluator()

    def __typing_subst__(self, arg):
        """Used for generic type substitution."""
        import typing
        return typing._typevar_subst(self, arg)

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of TypeVar")


@_attr_guard(
    readonly={'__name__', '__bound__', '__covariant__', '__contravariant__',
              '__infer_variance__'},
    not_writable={'args', 'kwargs'},
)
class ParamSpec(_Immutable, _PickleUsingNameMixin, _BoundVarianceMixin):
    """Parameter specification variable.

    The preferred way to construct a parameter specification is via the
    dedicated syntax for generic functions, classes, and type aliases,
    where the use of ``**`` creates a parameter specification::

        type IntFunc[**P] = Callable[P, int]

    For compatibility with Python 3.11 and earlier, ParamSpec objects
    can also be created as follows::

        P = ParamSpec('P')

    Parameter specification variables exist primarily for the benefit of
    static type checkers.  They are used to forward the parameter types of
    one callable to another callable, a pattern commonly found in
    higher-order functions and decorators.  They are only valid when used
    in ``Concatenate``, or as the first argument to ``Callable``, or as
    parameters for user-defined Generics.  See class Generic for more
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
        object.__setattr__(self, '__name__', name)
        super().__init__(bound, covariant, contravariant, infer_variance)
        object.__setattr__(self, '__module__', _caller_module())

    @property
    def args(self):
        return ParamSpecArgs(self)

    @property
    def kwargs(self):
        return ParamSpecKwargs(self)

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

    ParamSpecArgs should not be used directly, but only accessed from
    a ParamSpec object.
    """
    __slots__ = ('__weakref__', '__origin__',)

    def __init__(self, origin):
        self.__origin__ = origin

    def __repr__(self):
        return f"{self.__origin__.__name__}.args"

    def __eq__(self, other):
        if isinstance(other, ParamSpecArgs):
            return self.__origin__ == other.__origin__
        return NotImplemented

    __hash__ = None

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of ParamSpecArgs")


class ParamSpecKwargs:
    """The kwargs for a ParamSpec object.

    Given P = ParamSpec('P'), P.kwargs is an instance of ParamSpecKwargs.

    ParamSpecKwargs should not be used directly, but only accessed from
    a ParamSpec object.
    """
    __slots__ = ('__weakref__', '__origin__',)

    def __init__(self, origin):
        self.__origin__ = origin

    def __repr__(self):
        return f"{self.__origin__.__name__}.kwargs"

    def __eq__(self, other):
        if isinstance(other, ParamSpecKwargs):
            return self.__origin__ == other.__origin__
        return NotImplemented

    __hash__ = None

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of ParamSpecKwargs")


@_attr_guard(readonly={'__name__'})
class TypeVarTuple(_Immutable, _PickleUsingNameMixin):
    """Type variable tuple. A specialized form of type variable
    that enables variadic generics.

    The preferred way to construct a type variable tuple is via the
    dedicated syntax for generic functions, classes, and type aliases,
    where a single '*' indicates a type variable tuple::

        def move_first_element_to_last[T, *Ts](tup: tuple[T, *Ts]) -> tuple[*Ts, T]:
            return (*tup[1:], tup[0])

    For compatibility with Python 3.11 and earlier, TypeVarTuple objects
    can also be created as follows::

        Ts = TypeVarTuple('Ts')

    And used like this in older versions of Python::

        class Array(Generic[*Ts]):
            ...

    Type variable tuples can be used in ``Callable``, ``Tuple``,
    ``Concatenate``, and in generic functions, classes, and type
    aliases::

        class Array[*Ts]: ...

        def foo[*Ts](*args: *Ts) -> tuple[*Ts]: ...

    """

    def __init__(self, name):
        object.__setattr__(self, '__name__', name)
        object.__setattr__(self, '__module__', _caller_module())

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


@_attr_guard(
    readonly={'__name__'},
    not_writable={'__value__', '__type_params__', '__parameters__', '__module__'},
    strict=True,
)
class TypeAliasType(_PickleUsingNameMixin):
    """Type alias.

    Type aliases are created through the type statement::

        type Alias = int

    In this example, Alias and int will be treated equivalently by static
    type checkers.

    At runtime, Alias is an instance of TypeAliasType. The __name__
    attribute holds the name of the type alias. The value of the alias
    is not stored as an attribute on the TypeAliasType object itself,
    but is instead accessed through the __value__ attribute, which
    dynamically evaluates the value. To create a generic type alias,
    use a syntax similar to what is used for generic classes and
    functions::

        type ListOrSet[T] = list[T] | set[T]

    """

    def __init__(self, name, value, *, type_params=()):
        if type_params is not None and not isinstance(type_params, tuple):
            raise TypeError("type_params must be a tuple")
        object.__setattr__(self, '__name__', name)
        object.__setattr__(self, '__type_params__',
                           tuple(type_params) if type_params else ())
        object.__setattr__(self, '__value__', value)
        object.__setattr__(self, '__module__', _caller_module())

    @property
    def __parameters__(self):
        """Return the type parameters, unpacking any TypeVarTuples."""
        if not self.__type_params__:
            return ()
        result = []
        for param in self.__type_params__:
            if isinstance(param, TypeVarTuple):
                result.extend(param)
            else:
                result.append(param)
        return tuple(result)

    __value__ = _LazyEvaluator()

    def __repr__(self):
        return self.__name__

    def __getitem__(self, parameters):
        """Support generic type alias subscripting: Alias[T]."""
        if not self.__type_params__:
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
    import sys
    t = TypeVar(name, infer_variance=True)
    object.__setattr__(t, '__module__',
                       sys._getframe(1).f_globals.get('__name__'))
    return t


def _make_typevar_with_bound(name, evaluate_bound):
    import sys
    t = TypeVar(name, infer_variance=True)
    object.__delattr__(t, '__bound__')
    object.__setattr__(t, '__evaluate_bound__', evaluate_bound)
    object.__setattr__(t, '__module__',
                       sys._getframe(1).f_globals.get('__name__'))
    return t


def _make_typevar_with_constraints(name, evaluate_constraints):
    import sys
    t = TypeVar(name, infer_variance=True)
    object.__delattr__(t, '__constraints__')
    object.__setattr__(t, '__evaluate_constraints__', evaluate_constraints)
    object.__setattr__(t, '__module__',
                       sys._getframe(1).f_globals.get('__name__'))
    return t


def _make_paramspec(name):
    import sys
    t = ParamSpec(name, infer_variance=True)
    object.__setattr__(t, '__module__',
                       sys._getframe(1).f_globals.get('__name__'))
    return t


def _make_typevartuple(name):
    import sys
    t = TypeVarTuple(name)
    object.__setattr__(t, '__module__',
                       sys._getframe(1).f_globals.get('__name__'))
    return t


def _make_typealiastype(name, evaluate_value, type_params):
    import sys
    t = TypeAliasType(name, None, type_params=type_params)
    object.__delattr__(t, '__value__')
    object.__setattr__(t, '__evaluate_value__', evaluate_value)
    object.__setattr__(t, '__module__',
                       sys._getframe(1).f_globals.get('__name__'))
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
    __slots__ = ('__weakref__',)
    _is_protocol = False

    def __class_getitem__(cls, params):
        import typing
        return typing._generic_class_getitem(cls, params)

    def __init_subclass__(cls, *args, **kwargs):
        import typing
        return typing._generic_init_subclass(cls, *args, **kwargs)
