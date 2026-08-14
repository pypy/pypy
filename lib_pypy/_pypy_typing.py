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

import sys

__all__ = [
    'TypeVar', 'ParamSpec', 'TypeVarTuple', 'TypeAliasType',
    'ParamSpecArgs', 'ParamSpecKwargs', 'Generic',
]


def _caller_module():
    # Return the __name__ of the module that called the __init__ invoking this
    # helper (frame 0 is _caller_module, frame 1 is the __init__, frame 2 is
    # its caller). Mirrors CPython's caller() in Objects/typevarobject.c, which
    # sets __module__ on explicitly constructed type variables to the defining
    # module (needed so they can be pickled by qualified name).
    try:
        f = sys._getframe(2)
    except ValueError:
        return None
    return f.f_globals.get('__name__')


class _Immutable:
    """Mixin reproducing how the C implementations reject attribute changes.

    Which assignments are rejected, and with which wording, follows from the
    struct layout of the corresponding C type, so each class spells its layout
    out:

    * _readonly_attrs lists every attribute that cannot be assigned.  Those
      are READONLY struct members, which report "readonly attribute".
    * _getset_attrs is the subset of them that is a getset without a setter;
      those report their own, more specific message.
    * _has_instance_dict is False for the types declared without
      Py_TPFLAGS_MANAGED_DICT: their instances have nowhere to store an
      unknown name, so every other attribute is rejected too.  The types that
      do have a dict accept new attributes (typing_extensions patches
      'has_default' onto TypeVar/ParamSpec instances on Python < 3.13).

    Internal code that legitimately needs to fill one of the readonly
    attributes in goes through object.__setattr__/object.__delattr__.
    """
    __slots__ = ()

    _readonly_attrs = frozenset()
    _getset_attrs = frozenset()
    _has_instance_dict = True

    def _immutable_error(self, name):
        cls = type(self)
        qualname = '%s.%s' % (cls.__module__, cls.__qualname__)
        if name in self._getset_attrs:
            return AttributeError(
                "attribute '%s' of '%s' objects is not writable"
                % (name, qualname))
        if name in self._readonly_attrs:
            return AttributeError("readonly attribute")
        if not self._has_instance_dict:
            return AttributeError(
                "'%s' object has no attribute '%s'" % (qualname, name))
        return None

    def __setattr__(self, name, value):
        error = self._immutable_error(name)
        if error is not None:
            raise error
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        error = self._immutable_error(name)
        if error is not None:
            raise error
        object.__delattr__(self, name)

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
            bound = _type_check(bound, "Bound must be a type.")
        else:
            bound = None
        object.__setattr__(self, '__bound__', bound)

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


class TypeVar(_Immutable, _PickleUsingNameMixin, _BoundVarianceMixin):
    """Type variable with support for lazy bound/constraints evaluation.

    Usage::

      T = TypeVar('T')  # Can be anything
      A = TypeVar('A', str, bytes)  # Must be str or bytes

    Type variables exist primarily for the benefit of static type
    checkers.  They serve as the parameters for generic types as well
    as for generic function definitions.
    """

    _readonly_attrs = frozenset((
        '__name__', '__bound__', '__covariant__', '__contravariant__',
        '__infer_variance__', '__constraints__',
    ))
    _getset_attrs = frozenset(('__bound__', '__constraints__'))

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
            constraints = tuple(_type_check(t, msg) for t in constraints)
        else:
            constraints = ()
        object.__setattr__(self, '__constraints__', constraints)

        object.__setattr__(self, '__module__', _caller_module())

    __bound__ = _LazyEvaluator()
    __constraints__ = _LazyEvaluator()

    def __typing_subst__(self, arg):
        """Used for generic type substitution."""
        import typing
        return typing._typevar_subst(self, arg)

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of TypeVar")

    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'typing.TypeVar' is not an acceptable base type")


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

    _readonly_attrs = frozenset((
        '__name__', '__bound__', '__covariant__', '__contravariant__',
        '__infer_variance__', 'args', 'kwargs',
    ))
    _getset_attrs = frozenset(('args', 'kwargs'))

    def __init__(self, name, *, bound=None, covariant=False, contravariant=False, infer_variance=False):
        object.__setattr__(self, '__name__', name)
        super().__init__(bound, covariant, contravariant, infer_variance)

        object.__setattr__(self, '__module__', _caller_module())

        # Create args and kwargs attributes
        object.__setattr__(self, 'args', ParamSpecArgs(self))
        object.__setattr__(self, 'kwargs', ParamSpecKwargs(self))

    def __typing_subst__(self, arg):
        import typing
        return typing._paramspec_subst(self, arg)

    def __typing_prepare_subst__(self, alias, args):
        import typing
        return typing._paramspec_prepare_subst(self, alias, args)

    def __mro_entries__(self, bases):
        raise TypeError("Cannot subclass an instance of ParamSpec")

    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'typing.ParamSpec' is not an acceptable base type")


class ParamSpecArgs(_Immutable):
    """The args for a ParamSpec object.

    Given P = ParamSpec('P'), P.args is an instance of ParamSpecArgs.
    """
    __slots__ = ('__origin__',)

    _readonly_attrs = frozenset(('__origin__',))
    _has_instance_dict = False

    def __init__(self, origin):
        object.__setattr__(self, '__origin__', origin)

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

    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'typing.ParamSpecArgs' is not an acceptable base type")


class ParamSpecKwargs(_Immutable):
    """The kwargs for a ParamSpec object.

    Given P = ParamSpec('P'), P.kwargs is an instance of ParamSpecKwargs.
    """
    __slots__ = ('__origin__',)

    _readonly_attrs = frozenset(('__origin__',))
    _has_instance_dict = False

    def __init__(self, origin):
        object.__setattr__(self, '__origin__', origin)

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

    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'typing.ParamSpecKwargs' is not an acceptable base type")


class TypeVarTuple(_Immutable, _PickleUsingNameMixin):
    """Type variable tuple.

    Usage::

      Ts = TypeVarTuple('Ts')

    A TypeVarTuple is a placeholder for an *arbitrary* number of types.
    """

    _readonly_attrs = frozenset(('__name__',))

    __slots__ = ('__name__',)

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

    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'typing.TypeVarTuple' is not an acceptable base type")


class _TypeAliasTypeMeta(type):
    """Metaclass matching CPython's non-subclassable, immutable TypeAliasType.

    Class-body entries are installed by type.__new__, so all later attribute
    assignment and deletion can be rejected here.
    """

    def __setattr__(cls, name, value):
        type_name = '%s.%s' % (cls.__module__, cls.__qualname__)
        raise TypeError(
            "cannot set %r attribute of immutable type %r" %
            (name, type_name))

    def __delattr__(cls, name):
        type_name = '%s.%s' % (cls.__module__, cls.__qualname__)
        raise TypeError(
            "cannot set %r attribute of immutable type %r" %
            (name, type_name))


class TypeAliasType(_Immutable, metaclass=_TypeAliasTypeMeta):
    """Runtime representation of a type alias created with PEP 695 syntax.

    The __value__ is lazily evaluated - the evaluate_func is called
    only when __value__ is first accessed, then cached.

    Example::

        type Point = tuple[float, float]
        # Point is a TypeAliasType with __name__ = 'Point'
        # and __value__ = tuple[float, float]
    """

    __module__ = 'typing'

    # _PickleUsingNameMixin has no __slots__, so inheriting from it would add
    # an instance dictionary.  TypeAliasType has fixed storage in CPython.
    __slots__ = ('__name_value', '__type_params_value', '__value_value',
                 '__evaluate_value', '__module_value')

    _readonly_attrs = frozenset((
        '__name__', '__parameters__', '__type_params__', '__value__',
        '__module__',
    ))
    _getset_attrs = frozenset((
        '__parameters__', '__type_params__', '__value__', '__module__',
    ))
    _has_instance_dict = False

    def __init__(self, name, value, *, type_params=()):
        """Initialize a TypeAliasType.

        Args:
            name: The name of the type alias.
            value: The value of the type alias.
            type_params: The type parameters of the alias (for generic aliases).
        """
        try:
            object.__getattribute__(self, '_TypeAliasType__name_value')
        except AttributeError:
            pass
        else:
            # CPython leaves an existing alias unchanged when __init__ is
            # invoked again directly.
            return
        if not isinstance(name, str):
            type_name = 'None' if name is None else type(name).__name__
            raise TypeError(
                f"typealias() argument 'name' must be str, not {type_name}"
            )
        if not isinstance(type_params, tuple):
            raise TypeError("type_params must be a tuple")
        object.__setattr__(self, '_TypeAliasType__name_value', name)
        object.__setattr__(self, '_TypeAliasType__type_params_value',
                           type_params)
        object.__setattr__(self, '_TypeAliasType__value_value', value)
        object.__setattr__(self, '_TypeAliasType__evaluate_value', None)
        object.__setattr__(self, '_TypeAliasType__module_value', _caller_module())

    @property
    def __name__(self):
        return self.__name_value

    @property
    def __type_params__(self):
        return self.__type_params_value

    def __getattribute__(self, name):
        # The class itself must expose TypeAliasType.__module__ == 'typing',
        # while each alias records the module that created it.  With no
        # instance dict, handle that intentional shadowing explicitly.
        if name == '__module__':
            return object.__getattribute__(
                self, '_TypeAliasType__module_value')
        return object.__getattribute__(self, name)

    @property
    def __parameters__(self):
        """Return the type parameters, unpacking any TypeVarTuples."""
        if not self.__type_params_value:
            return ()
        result = []
        for param in self.__type_params_value:
            if isinstance(param, TypeVarTuple):
                result.extend(param)
            else:
                result.append(param)
        return tuple(result)

    @property
    def __value__(self):
        evaluate_value = self.__evaluate_value
        if evaluate_value is not None:
            # Do not clear the evaluator until it succeeds: a failed lazy
            # lookup must be retried on the next access.
            value = evaluate_value()
            object.__setattr__(self, '_TypeAliasType__value_value', value)
            object.__setattr__(self, '_TypeAliasType__evaluate_value', None)
        return self.__value_value

    def __reduce__(self):
        return self.__name__

    def __repr__(self):
        return self.__name_value

    def __getitem__(self, parameters):
        """Support generic type alias subscripting: Alias[T]."""
        if not self.__type_params_value:
            raise TypeError("Only generic type aliases are subscriptable")
        # Prefer types.GenericAlias so specialized aliases match CPython's
        # types.GenericAlias (and its list/tuple repr rules).
        import types
        return types.GenericAlias(self, parameters)

    def __or__(self, other):
        """Support | for types.UnionType."""
        from _pypy_generic_alias import _create_union
        return _create_union(self, other)

    def __ror__(self, other):
        """Support | for types.UnionType (reverse)."""
        from _pypy_generic_alias import _create_union
        return _create_union(other, self)

    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'typing.TypeAliasType' is not an acceptable base type")


# Factory functions for the compiler
# These are called from generated bytecode to create type parameters
# with lazy evaluation support.

def _make_typevar(name):
    t = TypeVar(name, infer_variance=True)
    object.__setattr__(t, '__module__', 'typing')
    return t


def _make_typevar_with_bound(name, evaluate_bound):
    t = TypeVar(name, infer_variance=True)
    object.__delattr__(t, '__bound__')
    object.__setattr__(t, '__evaluate_bound__', evaluate_bound)
    object.__setattr__(t, '__module__', 'typing')
    return t


def _make_typevar_with_constraints(name, evaluate_constraints):
    t = TypeVar(name, infer_variance=True)
    object.__delattr__(t, '__constraints__')
    object.__setattr__(t, '__evaluate_constraints__', evaluate_constraints)
    object.__setattr__(t, '__module__', 'typing')
    return t


def _make_paramspec(name):
    t = ParamSpec(name, infer_variance=True)
    object.__setattr__(t, '__module__', 'typing')
    return t


def _make_typevartuple(name):
    t = TypeVarTuple(name)
    object.__setattr__(t, '__module__', 'typing')
    return t


def _make_typealiastype(name, evaluate_value, type_params):
    t = TypeAliasType(name, None, type_params=type_params)
    object.__setattr__(t, '_TypeAliasType__evaluate_value', evaluate_value)
    object.__setattr__(t, '_TypeAliasType__module_value',
                       getattr(evaluate_value, '__module__', None))
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
        # PEP 695: the compiler builds the implicit Generic[...] base from a
        # tuple of the class's bare type params (Generic[(T, Ts, P)], always
        # a genuine tuple, built by BUILD_TUPLE). CPython's
        # _Py_subscript_generic intrinsic unpacks any TypeVarTuple (Ts -> *Ts)
        # before the subscript, which _generic_class_getitem then requires (a
        # bare TypeVarTuple is not "type-var-like"). PyPy routes that
        # intrinsic through Generic.__class_getitem__ itself, so mirror the
        # unpacking here -- but only for that specific cls-is-Generic, tuple
        # call shape. An ordinary bare TypeVarTuple subscript of Generic
        # itself (`Generic[Ts]`, no comma) is user code, not the compiler,
        # and must stay invalid; likewise subscripting an already-defined
        # subclass (`SomeGeneric[Ts]`) must leave a bare Ts as an
        # unsubstitutable placeholder rather than silently unpacking it.
        if cls is Generic and isinstance(params, tuple):
            params = tuple(
                typing.Unpack[p] if isinstance(p, typing.TypeVarTuple) else p
                for p in params)
        return typing._generic_class_getitem(cls, params)

    def __init_subclass__(cls, *args, **kwargs):
        import typing
        return typing._generic_init_subclass(cls, *args, **kwargs)


# make the __module__ match pickling by their public name.
for _cls in (TypeVar, ParamSpec, TypeVarTuple, Generic,
             ParamSpecArgs, ParamSpecKwargs):
    _cls.__module__ = 'typing'
del _cls
