from pypy.interpreter.error import OperationError, debug_print
from pypy.interpreter import baseobjspace
from pypy.interpreter import eval
from pypy.interpreter.function import Function
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objspace import W_Object, StdObjSpace
from pypy.objspace.std.model import UnwrapError
from pypy.tool.cache import Cache 

# this file automatically generates non-reimplementations of CPython
# types that we do not yet implement in the standard object space
# (files being the biggy)


def fake_object(space, x):
    if isinstance(x, type):
        ft = fake_type(x)
        return space.gettypeobject(ft.typedef)
    ft = fake_type(type(x))
    return ft(space, x)


import sys

_fake_type_cache = Cache()

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
        w_exc = space.wrap(exc)
        w_value = space.wrap(value)
    raise OperationError, OperationError(w_exc, w_value), tb

def fake_type(cpy_type):
    assert type(cpy_type) is type
    return _fake_type_cache.getorbuild(cpy_type, really_build_fake_type, None)

def really_build_fake_type(cpy_type, ignored):
    "NOT_RPYTHON (not remotely so!)."
    debug_print('faking %r'%(cpy_type,))
    kw = {}
    
    if cpy_type.__name__ == 'SRE_Pattern':
        import re
        import __builtin__
        p = re.compile("foo")
        for meth_name in p.__methods__:
            kw[meth_name] = __builtin__.eval("lambda p,*args,**kwds: p.%s(*args,**kwds)" % meth_name)
    elif cpy_type.__name__ == 'SRE_Match':
        import re
        import __builtin__
        m = re.compile("foo").match('foo')
        for meth_name in m.__methods__:
            kw[meth_name] = __builtin__.eval("lambda m,*args,**kwds: m.%s(*args,**kwds)" % meth_name)
    else:
        for s, v in cpy_type.__dict__.items():
            if not (cpy_type is unicode and s in ['__add__', '__contains__']):
                if s != '__getattribute__' or cpy_type is type(sys):
                    kw[s] = v

    kw['__module__'] = cpy_type.__module__

    def fake__new__(space, w_type, args_w):
        args = [space.unwrap(w_arg) for w_arg in args_w]
        try:
            r = cpy_type.__new__(cpy_type, *args)
        except:
            wrap_exception(space)
        w_obj = space.allocate_instance(W_Fake, w_type)
        w_obj.__init__(space, r)
        return w_obj

    kw['__new__'] = gateway.interp2app(fake__new__,
                         unwrap_spec = [baseobjspace.ObjSpace,
                                        baseobjspace.W_Root,
                                        'args_w'])
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
            W_Object.__init__(w_self, space)
            w_self.val = val
        def unwrap(w_self):
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
    def create_frame(self, space, w_globals, closure=None):
        return CPythonFakeFrame(space, self, w_globals)
    def signature(self):
        return [], 'args', 'kwds'

class CPythonFakeFrame(eval.Frame):

    def setfastscope(self, scope_w):
        w_args, w_kwds = scope_w
        try:
            self.unwrappedargs = self.space.unwrap(w_args)
            self.unwrappedkwds = self.space.unwrap(w_kwds)
        except UnwrapError, e:
            raise UnwrapError('calling %s: %s' % (self.code.cpy_callable, e))

    def getfastscope(self):
        raise OperationError(self.space.w_TypeError,
          self.space.wrap("cannot get fastscope of a CPythonFakeFrame"))                           
    def run(self):
        fn = self.code.cpy_callable
        try:
            result = apply(fn, self.unwrappedargs, self.unwrappedkwds)
        except:
            wrap_exception(self.space)
        return self.space.wrap(result)

def fake_builtin_callable(space, val):
    return Function(space, CPythonFakeCode(val))

_fake_type_cache.content[type(len)] = fake_builtin_callable
_fake_type_cache.content[type(list.append)] = fake_builtin_callable
_fake_type_cache.content[type(type(None).__repr__)] = fake_builtin_callable


from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

class W_FakeDescriptor(Wrappable):
    # Mimics pypy.interpreter.typedef.GetSetProperty.

    def __init__(self, space, d):
        self.name = d.__name__

    def descr_descriptor_get(space, w_descriptor, w_obj, w_cls=None):
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if w_obj == space.w_None and not space.is_true(space.is_(w_cls, space.type(space.w_None))):
            #print w_descriptor, w_obj, w_cls
            return w_descriptor
        else:
            name = space.unwrap(w_descriptor).name
            obj = space.unwrap(w_obj)
            try:
                val = getattr(obj, name)  # this gives a "not RPython" warning
            except:
                wrap_exception(space)
            return space.wrap(val)

    def descr_descriptor_set(space, w_descriptor, w_obj, w_value):
        name = space.unwrap(w_descriptor).name
        obj = space.unwrap(w_obj)
        val = space.unwrap(w_value)
        try:
            setattr(obj, name, val)   # this gives a "not RPython" warning
        except:
            wrap_exception(space)

    def descr_descriptor_del(space, w_descriptor, w_obj):
        name = space.unwrap(w_descriptor).name
        obj = space.unwrap(w_obj)
        try:
            delattr(obj, name)
        except:
            wrap_exception(space)

    typedef = TypeDef("FakeDescriptor",
        __get__ = interp2app(descr_descriptor_get),
        __set__ = interp2app(descr_descriptor_set),
        __delete__ = interp2app(descr_descriptor_del),
        )

_fake_type_cache.content[type(file.softspace)] = W_FakeDescriptor
_fake_type_cache.content[type(type.__dict__['__dict__'])] = W_FakeDescriptor
