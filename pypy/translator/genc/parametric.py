import types


class parametrictype(type):
    """The metaclass of parametric type classes."""

    def __getitem__(cls, key):
        if '_parametrizedinstances_' not in cls.__dict__:
            cls._parametrizedinstances_ = {}
        elif cls._parametrizedinstances_ is None:
            raise TypeError, "'%s' is already specialized" % cls.__name__
        try:
            return cls._parametrizedinstances_[key]
        except KeyError:
            keyrepr = recrepr(key)
            if keyrepr.startswith('(') and keyrepr.endswith(')') and key != ():
                keyrepr = keyrepr[1:-1]
            newname = '%s[%s]' % (cls.__name__, keyrepr)
            CType_Parametrized = type(cls)(newname, (cls,), {
                '_parametrizedinstances_': None,
                '__module__': cls.__module__,
                })
            cls._parametrizedinstances_[key] = CType_Parametrized
            for basecls in CType_Parametrized.__mro__:
                raw = basecls.__dict__.get('__initsubclass__')
                if isinstance(raw, types.FunctionType):
                    raw(CType_Parametrized, key)   # call it as a class method
            return CType_Parametrized


def recrepr(key):
    if isinstance(key, tuple):
        items = [recrepr(x) for x in key]
        if len(items) == 1:
            return '(%s,)' % (items[0],)
        else:
            return '(%s)' % (', '.join(items),)
    try:
        return key.__name__
    except AttributeError:
        return repr(key)
