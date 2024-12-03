_ATTR_EXCEPTIONS = frozenset((
    "__args__",
    "__class__",
    "__copy__",
    "__deepcopy__",
    "__mro_entries__",
    "__origin__",
    "__parameters__",
    "__reduce__",
    "__reduce_ex__",  # needed so we don't look up object.__reduce_ex__
    "__typing_unpacked_tuple_args__",
    "__unpacked__",
))

class GenericAlias:

    __slots__ = ("__weakref__", "_origin", "_args", "_parameters", "_hash", "__unpacked__")

    def __new__(cls, origin, args):
        result = super(GenericAlias, cls).__new__(cls)
        if not isinstance(args, tuple):
            args = (args, )
        result._origin = origin
        result._args = args
        result._parameters = _collect_parameters(args)
        result.__unpacked__ = False
        return result

    @property
    def __origin__(self):
        return object.__getattribute__(self, "_origin")

    @property
    def __args__(self):
        return object.__getattribute__(self, "_args")

    @property
    def __parameters__(self):
        return object.__getattribute__(self, "_parameters")

    def __call__(self, *args, **kwargs):
        result = self.__origin__(*args, **kwargs)
        try:
            result.__orig_class__ = self
        except (AttributeError, TypeError):
            pass
        return result

    def __mro_entries__(self, orig_bases):
        return (self.__origin__, )

    def __getattribute__(self, name):
        if name not in _ATTR_EXCEPTIONS:
            return getattr(self.__origin__, name)
        return object.__getattribute__(self, name)

    def __repr__(self):
        inner = ', '.join([_repr_item(x) for x in self.__args__])
        if len(self.__args__) == 0:
            inner = "()"
        star = '*' if self.__unpacked__ else ''
        return f"{star}{_repr_item(self.__origin__)}[{inner}]"

    def __eq__(self, other):
        if not isinstance(other, GenericAlias):
            return NotImplemented
        return (self.__origin__ == other.__origin__ and
                self.__args__ == other.__args__ and
                self.__unpacked__ == other.__unpacked__)

    def __getitem__(self, items):
        if not isinstance(items, tuple):
            items = (items, )
        params = self.__parameters__
        args = self.__args__
        newargs = subs_parameters(self, args, params, items)
        res = GenericAlias(self.__origin__, tuple(newargs))
        if self.__unpacked__:
            res.__unpacked__ = True
        return res

    def __hash__(self):
        return hash(self.__origin__) ^ hash(self.__args__)

    def __dir__(self):
        cls = type(self)
        dir_origin = set(dir(self.__origin__))
        return sorted(_ATTR_EXCEPTIONS | dir_origin)

    def __subclasscheck__(self, other):
        raise TypeError("issubclass() argument 2 cannot be a parameterized generic")

    def __instancecheck__(self, other):
        raise TypeError("isinstance() argument 2 cannot be a parameterized generic")

    def __reduce__(self):
        if self.__unpacked__:
            orig = GenericAlias(self.__origin__, self.__args__)
            return (_make_starred, (orig, ))
        return (type(self), (self.__origin__, self.__args__))

    def __or__(self, other):
        return _create_union(self, other)

    def __ror__(self, other):
        return _create_union(other, self)

    def __iter__(self):
        yield _make_starred(self)

    @property
    def __typing_unpacked_tuple_args__(self):
        if self.__unpacked__ and self.__origin__ is tuple:
            return self.__args__
        return None


def _make_starred(ga):
    res = GenericAlias(ga.__origin__, ga.__args__)
    res.__unpacked__ = True
    return res


def _repr_item(it):
    import typing
    if it == Ellipsis:
        return "..."
    if isinstance(it, GenericAlias):
        return repr(it)
    if isinstance(it, typing._GenericAlias):
        return repr(it)
    try:
        qualname = getattr(it, "__qualname__")
        module = getattr(it, "__module__")
        if module == "builtins":
            return qualname
        return f"{module}.{qualname}"
    except AttributeError:
        return repr(it)

def _repr_item_union(it):
    if it is type(None):
        return "None"
    return _repr_item(it)

def _is_typevar(v):
    t = type(v)
    return t.__name__ == "TypeVar" and t.__module__ == "typing"

def _collect_parameters(args):
    """Collect all type variables and parameter specifications in args
    in order of first appearance (lexicographic order).

    For example::

        >>> P = ParamSpec('P')
        >>> T = TypeVar('T')
        >>> _collect_parameters((T, Callable[P, T]))
        (~T, ~P)
    """
    # copied from typing.py, for bootstrapping reasons
    parameters = []
    for t in args:
        if isinstance(t, type):
            # We don't want __parameters__ descriptor of a bare Python class.
            pass
        elif isinstance(t, tuple):
            # `t` might be a tuple, when `ParamSpec` is substituted with
            # `[T, int]`, or `[int, *Ts]`, etc.
            for x in t:
                for collected in _collect_parameters([x]):
                    if collected not in parameters:
                        parameters.append(collected)
        elif hasattr(t, '__typing_subst__'):
            if t not in parameters:
                parameters.append(t)
        else:
            for x in getattr(t, '__parameters__', ()):
                if x not in parameters:
                    parameters.append(x)
    return tuple(parameters)

def subs_tvars(obj, params, argitems):
    """If obj is a generic alias, substitute type variables params with
    substitutions argitems.  For example, if obj is list[T], params is (T, S),
    and argitems is (str, int), return list[str]. If obj doesn't have a
    __parameters__ attribute or that's not a non-empty tuple, return a new
    reference to obj. """
    from typing import TypeVarTuple
    subparams = getattr(obj, "__parameters__", ())
    if not subparams or not isinstance(subparams, tuple):
        return obj
    nparams = len(params)
    nsubparams = len(subparams)
    subargs = []
    for param in subparams:
        try:
            arg = argitems[params.index(param)]
        except ValueError:
            arg = param
        if isinstance(param, TypeVarTuple):
            subargs.extend(arg)
        else:
            subargs.append(arg)
    return obj[tuple(subargs)]

def subs_parameters(self, args, params, items):
    from typing import _is_unpacked_typevartuple, _unpack_args
    nparams = len(params)
    if nparams == 0:
        raise TypeError(f"{self!r} is not a generic class")
    items = _unpack_args(items)
    for param in params:
        prepare = getattr(param, '__typing_prepare_subst__', None)
        if prepare is not None:
            items = prepare(self, items)
    nitems = len(items)
    if nparams != nitems:
        direction = 'many' if nitems > nparams else 'few'
        raise TypeError(f"Too {direction} arguments for {self}; actual {nitems}, expected {nparams}")
    newargs = []
    for i, old_arg in enumerate(args):
        if isinstance(old_arg, type):
            newargs.append(old_arg)
            continue
        unpack = _is_unpacked_typevartuple(old_arg)
        meth = getattr(old_arg, '__typing_subst__', None)
        if meth is not None:
            iparam = params.index(old_arg)
            arg = meth(items[iparam])
        else:
            arg = subs_tvars(old_arg, params, items)
        if unpack:
            newargs.extend(arg)
        else:
            newargs.append(arg)

    return newargs

class UnionType:
    """
    Represent a PEP 604 union type

    E.g. for int | str
    """

    __slots__ = ("__weakref__", "_args", "__parameters__")

    def __init__(self, args):
        # need to deduplicate and flatten
        res = []
        todo = list(args)
        def add_recurse(arg):
            if arg is None:
                arg = type(None)
            if isinstance(arg, UnionType):
                for a in arg.__args__:
                    add_recurse(a)
            elif arg not in res:
                res.append(arg)
        for a in args:
            add_recurse(a)
        self._args = tuple(res)
        self.__parameters__ = _collect_parameters(args)

    @property
    def __args__(self):
        return object.__getattribute__(self, "_args")

    def __eq__(self, other):
        if not isinstance(other, UnionType):
            return NotImplemented
        return set(self.__args__) == set(other.__args__)

    def __hash__(self):
        return hash(frozenset(self.__args__))

    def __subclasscheck__(self, other):
        for cls in self.__args__:
            if isinstance(cls, GenericAlias):
                raise TypeError("issubclass() argument 2 cannot contain a parameterized generic")
        for cls in self.__args__:
            if cls is None:
                if other is type(None):
                    return True
            if issubclass(other, cls):
                return True
        return False

    def __instancecheck__(self, instance):
        for cls in self.__args__:
            if isinstance(cls, GenericAlias):
                raise TypeError("isinstance() argument 2 cannot contain a parameterized generic")
        for cls in self.__args__:
            if cls is None:
                if instance is None:
                    return True
            elif isinstance(instance, cls):
                return True
        return False

    def __repr__(self):
        ret = " | ".join([_repr_item_union(x) for x in self.__args__])
        return ret

    def __or__(self, other):
        return _create_union(self, other)

    def __ror__(self, other):
        return _create_union(other, self)

    def __getitem__(self, items):
        if not isinstance(items, tuple):
            items = (items, )
        params = self.__parameters__
        args = self.__args__
        newargs = subs_parameters(self, args, params, items)
        if len(newargs) == 0:
            return UnionType(())
        curr = newargs[0]
        for i in range(1, len(newargs)):
            curr |= newargs[i]
        return curr

def _unionable(obj):
    return obj is None or isinstance(obj, (type, UnionType, GenericAlias))

def _create_union(self, other):
    if _unionable(self) and _unionable(other):
        if self == other:
            return self
        return UnionType((self, other))
    return NotImplemented
