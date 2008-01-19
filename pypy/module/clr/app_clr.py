# NOT_RPYTHON

class StaticMethodWrapper(object):
    __slots__ = ('class_name', 'meth_name',)

    def __init__(self, class_name, meth_name):
        self.class_name = class_name
        self.meth_name = meth_name

    def __call__(self, *args):
        import clr
        return clr.call_staticmethod(self.class_name, self.meth_name, args)

    def __repr__(self):
        return '<static CLI method %s.%s>' % (self.class_name, self.meth_name)


class MethodWrapper(object):
    __slots__ = ('meth_name',)
    
    def __init__(self, meth_name):
        self.meth_name = meth_name

    def __get__(self, obj, type_):
        if obj is None:
            return UnboundMethod(type_, self.meth_name)
        else:
            return BoundMethod(self.meth_name, obj)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, repr(self.meth_name))


class UnboundMethod(object):
    __slots__ = ('im_class', 'im_name')
    
    def __init__(self, im_class, im_name):
        self.im_class = im_class
        self.im_name = im_name

    def __raise_TypeError(self, thing):
        raise TypeError, 'unbound method %s() must be called with %s ' \
              'instance as first argument (got %s instead)' % \
              (self.im_name, self.im_class.__cliclass__, thing)

    def __call__(self, *args):
        if len(args) == 0:
            self.__raise_TypeError('nothing')
        im_self = args[0]
        if not isinstance(im_self, self.im_class):
            self.__raise_TypeError('%s instance' % im_self.__class__.__name__)
        return im_self.__cliobj__.call_method(self.im_name, args, 1) # ignore the first arg

    def __repr__(self):
        return '<unbound CLI method %s.%s>' % (self.im_class.__cliclass__, self.im_name)


class BoundMethod(object):
    __slots__ = ('im_name', 'im_self')
    
    def __init__(self, im_name, im_self):
        self.im_name = im_name
        self.im_self = im_self

    def __call__(self, *args):
        return self.im_self.__cliobj__.call_method(self.im_name, args)

    def __repr__(self):
        return '<bound CLI method %s.%s of %s>' % (self.im_self.__class__.__cliclass__,
                                                   self.im_name,
                                                   self.im_self)

class StaticProperty(object):
    def __init__(self, fget=None, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, type_):
        return self.fget()

def _qualify(t):
    mscorlib = 'mscorlib, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089'
    return '%s, %s' % (t, mscorlib)

class MetaGenericCliClassWrapper(type):
    _cli_types = {
        int: _qualify('System.Int32'),
        str: _qualify('System.String'),
        bool: _qualify('System.Boolean'),
        float: _qualify('System.Double'),
        }
    _System_Object = _qualify('System.Object')

    def _cli_name(cls, ttype):
        if isinstance(ttype, MetaCliClassWrapper):
            return '[%s]' % ttype.__fullyqualifiedname__
        else:
            return '[%s]' % cls._cli_types.get(ttype, cls._System_Object)
    
    def __setattr__(cls, name, value):
        obj = cls.__dict__.get(name, None)
        if isinstance(obj, StaticProperty):
            obj.fset(value)
        else:
            type.__setattr__(cls, name, value)

    def __getitem__(cls, type_or_tuple):
        import clr
        if isinstance(type_or_tuple, tuple):
            types = type_or_tuple
        else:
            types = (type_or_tuple,)
        namespace, generic_class = cls.__cliclass__.rsplit('.', 1)
        generic_params = [cls._cli_name(t) for t in types]        
        instance_class = '%s[%s]' % (generic_class, ','.join(generic_params))
        try:
            return clr.load_cli_class(cls.__assemblyname__, namespace, instance_class)
        except ImportError:
            raise TypeError, "Cannot load type %s.%s" % (namespace, instance_class)

class MetaCliClassWrapper(type):
    def __setattr__(cls, name, value):
        obj = cls.__dict__.get(name, None)
        if isinstance(obj, StaticProperty):
            obj.fset(value)
        else:
            type.__setattr__(cls, name, value)

class CliClassWrapper(object):
    __slots__ = ('__cliobj__',)

    def __init__(self, *args):
        import clr
        self.__cliobj__ = clr._CliObject_internal(self.__fullyqualifiedname__, args)


class IEnumeratorWrapper(object):
    def __init__(self, enumerator):
        self.__enumerator__ = enumerator

    def __iter__(self):
        return self

    def next(self):
        if not self.__enumerator__.MoveNext():
            raise StopIteration
        return self.__enumerator__.Current

# this method need to be attached only to classes that implements IEnumerable (see build_wrapper)
def __iter__(self):
    return IEnumeratorWrapper(self.GetEnumerator())

def wrapper_from_cliobj(cls, cliobj):
    obj = cls.__new__(cls)
    obj.__cliobj__ = cliobj
    return obj

def build_wrapper(namespace, classname, assemblyname,
                  staticmethods, methods, properties, indexers,
                  hasIEnumerable, isClassGeneric):
    fullname = '%s.%s' % (namespace, classname)
    assembly_qualified_name = '%s, %s' % (fullname, assemblyname)
    d = {'__cliclass__': fullname,
         '__fullyqualifiedname__': assembly_qualified_name,
         '__assemblyname__': assemblyname,
         '__module__': namespace}
    for name in staticmethods:
        d[name] = StaticMethodWrapper(assembly_qualified_name, name)
    for name in methods:
        d[name] = MethodWrapper(name)

    # check if IEnumerable is implemented
    if hasIEnumerable:
        d['__iter__'] = __iter__

    assert len(indexers) <= 1
    if indexers:
        name, getter, setter, is_static = indexers[0]
        assert not is_static
        if getter:
            d['__getitem__'] = d[getter]
        if setter:
            d['__setitem__'] = d[setter]
    if isClassGeneric:
        cls = MetaGenericCliClassWrapper(classname, (CliClassWrapper,), d)
    else: 
        cls = MetaCliClassWrapper(classname, (CliClassWrapper,), d)

    # we must add properties *after* the class has been created
    # because we need to store UnboundMethods as getters and setters
    for (name, getter, setter, is_static) in properties:
        fget = None
        fset = None
        if getter:
            fget = getattr(cls, getter)
        if setter:
            fset = getattr(cls, setter)
        if is_static:
            prop = StaticProperty(fget, fset)
        else:
            prop = property(fget, fset)
        setattr(cls, name, prop)

    return cls
