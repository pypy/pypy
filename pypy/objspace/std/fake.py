from pypy.interpreter.error import OperationError
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objspace import W_Object, StdObjSpace
from pypy.objspace.std.default import UnwrapError

# this file automatically generates non-reimplementations of CPython
# types that we do not yet implement in the standard object space
# (files being the biggy)

import sys

_fake_type_cache = {}

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
    if cpy_type in _fake_type_cache:
        return _fake_type_cache[cpy_type]
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
    def fake_unwrap(space, w_obj):
        return w_obj.val
    StdObjSpace.unwrap.register(fake_unwrap, W_Fake)
    W_Fake.__name__ = 'W_Fake%s'%(cpy_type.__name__.capitalize())
    W_Fake.typedef.fakedcpytype = cpy_type
    # XXX obviously this entire file is something of a hack, but it
    # manages to get worse here:
    if cpy_type is type(type(None).__repr__):
        def call_args(self, args):
            try:
                unwrappedargs = [self.space.unwrap(w_arg) for w_arg in args.args_w]
                unwrappedkwds = dict([(key, self.space.unwrap(w_value))
                                      for key, w_value in args.kwds_w.items()])
            except UnwrapError, e:
                raise UnwrapError('calling %s: %s' % (cpy_type, e))
            try:
                assert callable(self.val), self.val
                result = apply(self.val, unwrappedargs, unwrappedkwds)
            except:
                wrap_exception(self.space)
            return self.space.wrap(result)

        setattr(W_Fake, "call_args", call_args)
    _fake_type_cache[cpy_type] = W_Fake
    return W_Fake

