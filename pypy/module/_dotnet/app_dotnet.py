# NOT_RPYTHON

class StaticMethodWrapper(object):
    __slots__ = ('class_name', 'meth_name',)

    def __init__(self, class_name, meth_name):
        self.class_name = class_name
        self.meth_name = meth_name

    def __call__(self, *args):
        import _dotnet
        return _dotnet.call_staticmethod(self.class_name, self.meth_name, args)

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
        return '<bound CLI method %s.%s of %s>' % (self.im_self.__class__.__cliclass__, self.im_name, self.im_self)


class CliClassWrapper(object):
    __slots__ = ('__cliobj__',)

    def __init__(self):
        import _dotnet
        self.__cliobj__ = _dotnet._CliObject_internal(self.__cliclass__)


class ArrayList(CliClassWrapper):
    __cliclass__ = 'System.Collections.ArrayList'
    Add = MethodWrapper('Add')
    get_Item = MethodWrapper('get_Item')
    __getitem__ = get_Item
    IndexOf = MethodWrapper('IndexOf')


class Math(CliClassWrapper):
    __cliclass__ = 'System.Math'
    Abs = StaticMethodWrapper(__cliclass__, 'Abs')
