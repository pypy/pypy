"""
Plain Python definition of the builtin descriptors.
"""

# Descriptor code, shamelessly stolen to Raymond Hettinger:
#    http://users.rcn.com/python/download/Descriptor.htm
class property(object):
    __slots__ = ['fget', 'fset', 'fdel', '__doc__']

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc or ""   # XXX why:  or ""  ?

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self         
        if self.fget is None:
            raise AttributeError, "unreadable attribute"
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError, "can't set attribute"
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError, "can't delete attribute"
        self.fdel(obj)


# XXX there is an interp-level pypy.interpreter.function.StaticMethod
# XXX because __new__ needs to be a StaticMethod early.
class staticmethod(object):
    __slots__ = ['_f']

    def __init__(self, f):
        self._f = f

    def __get__(self, obj, objtype=None):
        return self._f


class classmethod(object):
    __slots__ = ['_f']

    def __init__(self, f):
        self._f = f

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        def newfunc(*args, **kwargs):
            return self._f(klass, *args, **kwargs)
        return newfunc

# super is a modified version from Guido's tutorial
#     http://www.python.org/2.2.3/descrintro.html
# it exposes the same special attributes as CPython's.
class super(object):
    __slots__ = ['__thisclass__', '__self__', '__self_class__']
    def __init__(self, typ, obj=None):
        if obj is None:
            objcls = None        # unbound super object
        elif _issubtype(type(obj), type) and _issubtype(obj, type):
            objcls = obj         # special case for class methods
        elif _issubtype(type(obj), typ):
            objcls = type(obj)   # normal case
        else:
            objcls = getattr(obj, '__class__', type(obj))
            if not _issubtype(objcls, typ):
                raise TypeError, ("super(type, obj): "
                                  "obj must be an instance or subtype of type")
        self.__thisclass__ = typ
        self.__self__ = obj
        self.__self_class__ = objcls
    def __get__(self, obj, type=None):
        ga = object.__getattribute__
        if ga(self, '__self__') is None and obj is not None:
            return super(ga(self, '__thisclass__'), obj)
        else:
            return self
    def __getattribute__(self, attr):
        d = object.__getattribute__(self, '__dict__')
        if attr != '__class__' and d['__self_class__'] is not None:
            # we want super().__class__ to be the real class
            # and we don't do anything for unbound type objects
            mro = iter(d['__self_class__'].__mro__)
            for cls in mro:
                if cls is d['__thisclass__']:
                    break
            # Note: mro is an iterator, so the second loop
            # picks up where the first one left off!
            for cls in mro:
                try:                
                    x = cls.__dict__[attr]
                except KeyError:
                    continue
                if hasattr(x, '__get__'):
                    x = x.__get__(d['__self__'], type(d['__self__']))
                return x
        return object.__getattribute__(self, attr)     # fall-back
