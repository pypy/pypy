from pypy.interpreter.error import OperationError
from pypy.interpreter import eval
from pypy.interpreter.function import Function
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objspace import W_Object, StdObjSpace
from pypy.objspace.std.default import UnwrapError
from pypy.tool.cache import Cache 

# this file automatically generates non-reimplementations of CPython
# types that we do not yet implement in the standard object space
# (files being the biggy)

import sys

_fake_type_cache = Cache()

# real-to-wrapped exceptions
def wrap_exception(space):
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
    print 'faking %r'%(cpy_type,)
    kw = {}
    for s, v in cpy_type.__dict__.items():
        if cpy_type is not unicode or s not in ['__add__', '__contains__']:
            kw[s] = v
    def fake__new__(space, w_type, *args_w):
        args = [space.unwrap(w_arg) for w_arg in args_w]
        try:
            r = cpy_type.__new__(cpy_type, *args)
        except:
            wrap_exception(space)
        return W_Fake(space, r)
    kw['__new__'] = gateway.interp2app(fake__new__)
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
    # cannot write to W_Fake.__name__ in Python 2.2!
    W_Fake = type(W_Object)('W_Fake%s'%(cpy_type.__name__.capitalize()),
                            (W_Object,),
                            dict(W_Fake.__dict__.items()))
    def fake_unwrap(space, w_obj):
        return w_obj.val
    StdObjSpace.unwrap.register(fake_unwrap, W_Fake)
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
    def run(self):
        fn = self.code.cpy_callable
        w_args, w_kwds = self.fastlocals_w
        try:
            unwrappedargs = self.space.unwrap(w_args)
            unwrappedkwds = self.space.unwrap(w_kwds)
        except UnwrapError, e:
            raise UnwrapError('calling %s: %s' % (fn, e))
        try:
            result = apply(fn, unwrappedargs, unwrappedkwds)
        except:
            wrap_exception(self.space)
        return self.space.wrap(result)

def fake_builtin_callable(space, val):
    return Function(space, CPythonFakeCode(val))

_fake_type_cache.content[type(len)] = fake_builtin_callable
_fake_type_cache.content[type(list.append)] = fake_builtin_callable
_fake_type_cache.content[type(type(None).__repr__)] = fake_builtin_callable

from pypy.interpreter.typedef import GetSetProperty

def fake_descriptor(space, d):
    n = d.__name__
    return space.wrap(GetSetProperty(lambda x:getattr(x, n),
                                     lambda x,y:setattr(x, n, y)))

_fake_type_cache.content[type(file.softspace)] = fake_descriptor
_fake_type_cache.content[type(type.__dict__['__dict__'])] = fake_descriptor
