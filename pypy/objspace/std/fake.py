from pypy.interpreter.error import OperationError, debug_print
from pypy.interpreter import baseobjspace
from pypy.interpreter import eval
from pypy.interpreter.function import Function, BuiltinFunction
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.model import W_Object, UnwrapError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter import gateway, argument

# this file automatically generates non-reimplementations of CPython
# types that we do not yet implement in the standard object space
# (files being the biggy)


def fake_object(space, x):
    if isinstance(x, file): 
        debug_print("fake-wrapping interp file %s" % x)
    if isinstance(x, type):
        ft = fake_type(x)
        return space.gettypeobject(ft.typedef)
    #debug_print("faking obj %s" % x)
    ft = fake_type(type(x))
    return ft(space, x)
fake_object._annspecialcase_ = "override:fake_object"

import sys

_fake_type_cache = {}

# real-to-wrapped exceptions
def wrap_exception(space):
    """NOT_RPYTHON"""
    exc, value, tb = sys.exc_info()
    if exc is OperationError:
        raise exc, value, tb   # just re-raise it
    name = exc.__name__
    if hasattr(space, 'w_' + name):
        w_exc = getattr(space, 'w_' + name)
        w_value = space.call_function(w_exc,
            *[space.wrap(a) for a in value.args])
        for key, value in value.__dict__.items():
            if not key.startswith('_'):
                space.setattr(w_value, space.wrap(key), space.wrap(value))
    else:
        debug_print('likely crashes because of faked exception %s: %s' % (
            exc.__name__, value))
        w_exc = space.wrap(exc)
        w_value = space.wrap(value)
    raise OperationError, OperationError(w_exc, w_value), tb
wrap_exception._annspecialcase_ = "override:ignore"

def fake_type(cpy_type):
    assert type(cpy_type) is type
    try:
        return _fake_type_cache[cpy_type]
    except KeyError:
        faked_type = really_build_fake_type(cpy_type)
        _fake_type_cache[cpy_type] = faked_type
        return faked_type

def really_build_fake_type(cpy_type):
    "NOT_RPYTHON (not remotely so!)."
    #assert not issubclass(cpy_type, file), cpy_type
    debug_print('faking %r'%(cpy_type,))
    kw = {}
    
    if cpy_type.__name__ == 'SRE_Pattern':
        import re
        import __builtin__
        p = re.compile("foo")
        for meth_name in p.__methods__:
            kw[meth_name] = EvenMoreObscureWrapping(__builtin__.eval("lambda p,*args,**kwds: p.%s(*args,**kwds)" % meth_name))
    elif cpy_type.__name__ == 'SRE_Match':
        import re
        import __builtin__
        m = re.compile("foo").match('foo')
        for meth_name in m.__methods__:
            kw[meth_name] = EvenMoreObscureWrapping(__builtin__.eval("lambda m,*args,**kwds: m.%s(*args,**kwds)" % meth_name))
    else:
        for s, v in cpy_type.__dict__.items():
            if not (cpy_type is unicode and s in ['__add__', '__contains__']):
                if s != '__getattribute__' or cpy_type is type(sys) or cpy_type is type(Exception):
                    kw[s] = v

    kw['__module__'] = cpy_type.__module__

    def fake__new__(space, w_type, __args__):
        args_w, kwds_w = __args__.unpack()
        args = [space.unwrap(w_arg) for w_arg in args_w]
        kwds = {}
        for (key, w_value) in kwds_w.items():
            kwds[key] = space.unwrap(w_value)
        try:
            r = apply(cpy_type.__new__, [cpy_type]+args, kwds)
        except:
            wrap_exception(space)
            raise
        w_obj = space.allocate_instance(W_Fake, w_type)
        W_Fake.__init__(w_obj, space, r)
        return w_obj

    kw['__new__'] = gateway.interp2app(fake__new__,
                                       unwrap_spec=[baseobjspace.ObjSpace,
                                                    baseobjspace.W_Root,
                                                    argument.Arguments])
    if cpy_type.__base__ is not object:
        assert cpy_type.__base__ is basestring
        from pypy.objspace.std.basestringtype import basestring_typedef
        base = basestring_typedef
    else:
        base = None
    class W_Fake(W_Object):
        typedef = StdTypeDef(
            cpy_type.__name__, base, **kw)
        def __init__(w_self, space, val):
            w_self.val = val
        def unwrap(w_self, space):
            return w_self.val
                
    # cannot write to W_Fake.__name__ in Python 2.2!
    W_Fake = type(W_Object)('W_Fake%s'%(cpy_type.__name__.capitalize()),
                            (W_Object,),
                            dict(W_Fake.__dict__.items()))
    W_Fake.typedef.fakedcpytype = cpy_type
    return W_Fake

# ____________________________________________________________
#
# Special case for built-in functions, methods, and slot wrappers.

class CPythonFakeCode(eval.Code):
    def __init__(self, cpy_callable):
        eval.Code.__init__(self, getattr(cpy_callable, '__name__', '?'))
        self.cpy_callable = cpy_callable
        assert callable(cpy_callable), cpy_callable
    def signature(self):
        return [], 'args', 'kwds'

class CPythonFakeFrame(eval.Frame):

    def __init__(self, space, code, w_globals=None, numlocals=-1):
        self.fakecode = code
        eval.Frame.__init__(self, space, w_globals, numlocals)

    def getcode(self):
        return self.fakecode

    def setfastscope(self, scope_w):
        w_args, w_kwds = scope_w
        try:
            self.unwrappedargs = self.space.unwrap(w_args)
            self.unwrappedkwds = self.space.unwrap(w_kwds)
        except UnwrapError, e:
            code = self.fakecode
            assert isinstance(code, CPythonFakeCode)
            raise UnwrapError('calling %s: %s' % (code.cpy_callable, e))

    def getfastscope(self):
        raise OperationError(self.space.w_TypeError,
          self.space.wrap("cannot get fastscope of a CPythonFakeFrame"))                           
    def run(self):
        code = self.fakecode
        assert isinstance(code, CPythonFakeCode)
        fn = code.cpy_callable
        try:
            result = apply(fn, self.unwrappedargs, self.unwrappedkwds)
        except:
            wrap_exception(self.space)
            raise
        return self.space.wrap(result)

class EvenMoreObscureWrapping(baseobjspace.Wrappable):
    def __init__(self, val):
        self.val = val
    def __spacebind__(self, space):
        return fake_builtin_callable(space, self.val)

def fake_builtin_callable(space, val):
    return Function(space, CPythonFakeCode(val))

def fake_builtin_function(space, fn):
    func = fake_builtin_callable(space, fn)
    if fn.__self__ is None:
        func = BuiltinFunction(func)
    return func

_fake_type_cache[type(len)] = fake_builtin_function
_fake_type_cache[type(list.append)] = fake_builtin_callable
_fake_type_cache[type(type(None).__repr__)] = fake_builtin_callable

class W_FakeDescriptor(Wrappable):
    # Mimics pypy.interpreter.typedef.GetSetProperty.

    def __init__(self, space, d):
        self.name = d.__name__

    def descr_descriptor_get(space, descr, w_obj, w_cls=None):
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if (space.is_w(w_obj, space.w_None)
            and not space.is_w(w_cls, space.type(space.w_None))):
            #print descr, w_obj, w_cls
            return space.wrap(descr)
        else:
            name = descr.name
            obj = space.unwrap(w_obj)
            try:
                val = getattr(obj, name)  # this gives a "not RPython" warning
            except:
                wrap_exception(space)
                raise
            return space.wrap(val)

    def descr_descriptor_set(space, descr, w_obj, w_value):
        name = descr.name
        obj = space.unwrap(w_obj)
        val = space.unwrap(w_value)
        try:
            setattr(obj, name, val)   # this gives a "not RPython" warning
        except:
            wrap_exception(space)

    def descr_descriptor_del(space, descr, w_obj):
        name = descr.name
        obj = space.unwrap(w_obj)
        try:
            delattr(obj, name)
        except:
            wrap_exception(space)


W_FakeDescriptor.typedef = TypeDef(
    "FakeDescriptor",
    __get__ = gateway.interp2app(W_FakeDescriptor.descr_descriptor_get.im_func,
                         unwrap_spec = [baseobjspace.ObjSpace, W_FakeDescriptor,
                                        baseobjspace.W_Root,
                                        baseobjspace.W_Root]),
    __set__ = gateway.interp2app(W_FakeDescriptor.descr_descriptor_set.im_func,
                         unwrap_spec = [baseobjspace.ObjSpace, W_FakeDescriptor,
                                        baseobjspace.W_Root, baseobjspace.W_Root]),
    __delete__ = gateway.interp2app(W_FakeDescriptor.descr_descriptor_del.im_func,
                            unwrap_spec = [baseobjspace.ObjSpace, W_FakeDescriptor,
                                           baseobjspace.W_Root]),
    )

if hasattr(file, 'softspace'):    # CPython only
    _fake_type_cache[type(file.softspace)] = W_FakeDescriptor
_fake_type_cache[type(type.__dict__['__dict__'])] = W_FakeDescriptor
