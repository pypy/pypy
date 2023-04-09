_ATTR_EXCEPTIONS = frozenset((
    "__origin__",
    "__args__",
    "__parameters__",
    "__mro_entries__",
    "__reduce_ex__",  # needed so we don't look up object.__reduce_ex__
    "__reduce__",
    "__copy__",
    "__deepcopy__",
))

class GenericAlias:

    __slots__ = ("__weakref__", "_origin", "_args", "_parameters", "_hash")

    def __new__(cls, origin, args):
        result = super(GenericAlias, cls).__new__(cls)
        if not isinstance(args, tuple):
            args = (args, )
        result._origin = origin
        result._args = args
        result._parameters = _make_parameters(args)
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
        return f"{_repr_item(self.__origin__)}[{inner}]"

    def __eq__(self, other):
        if not isinstance(other, GenericAlias):
            return NotImplemented
        return self.__origin__ == other.__origin__ and self.__args__ == other.__args__

    def __getitem__(self, items):
        if not isinstance(items, tuple):
            items = (items, )
        params = self.__parameters__
        args = self.__args__
        newargs = subs_parameters(self, args, params, items)
        return GenericAlias(self.__origin__, tuple(newargs))

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
        return (type(self), (self.__origin__, self.__args__))

    def __or__(self, other):
        return _create_union(self, other)

    def __ror__(self, other):
        return _create_union(other, self)


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

def _make_parameters(args):
    res = []
    seen = set()
    def add(x):
        if x not in seen:
            seen.add(x)
            res.append(x)
    for arg in args:
        if _is_typevar(arg):
            add(arg)
        else:
            try:
                params = arg.__parameters__
            except AttributeError:
                pass
            else:
                if isinstance(params, tuple):
                    for param in params:
                        add(param)
    return tuple(res)

def subs_tvars(obj, params, argitems):
    """If obj is a generic alias, substitute type variables params with
    substitutions argitems.  For example, if obj is list[T], params is (T, S),
    and argitems is (str, int), return list[str]. If obj doesn't have a
    __parameters__ attribute or that's not a non-empty tuple, return a new
    reference to obj. """
    subparams = getattr(obj, "__parameters__", ())
    if not subparams or not isinstance(subparams, tuple):
        return obj
    nparams = len(params)
    nsubparams = len(subparams)
    subargs = []
    for arg in subparams:
        try:
            arg = argitems[params.index(arg)]
        except ValueError:
            pass
        subargs.append(arg)
    return obj[tuple(subargs)]

def subs_parameters(self, args, params, items):
    nparams = len(params)
    nitems = len(items)
    if nparams == 0:
        raise TypeError("There are no type variables left in %r" % self)
    if nparams != nitems:
        raise TypeError("mismatched arguments for %r" % self)
    args = args
    newargs = []
    for i, arg in enumerate(args):
        if _is_typevar(arg):
            iparam = params.index(arg)
            newargs.append(items[iparam])
        else:
            newargs.append(subs_tvars(arg, params, items))
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
        self.__parameters__ = _make_parameters(args)

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
