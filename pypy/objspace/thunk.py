"""Example usage:

    $ py.py -o thunk
    >>> from __pypy__ import thunk, lazy, become
    >>> def f():
    ...     print 'computing...'
    ...     return 6*7
    ...
    >>> x = thunk(f)
    >>> x
    computing...
    42
    >>> x
    42
    >>> y = thunk(f)
    >>> type(y)
    computing...
    <pypy type 'int'>

    >>> @lazy
    ... def g(n):
    ...     print 'computing...'
    ...     return n + 5
    ...
    >>> y = g(12)
    >>> y
    computing...
    17
"""

from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Method

# __________________________________________________________________________

# 'w_obj.w_thunkalias' points to another object that 'w_obj' has turned into
baseobjspace.W_Root.w_thunkalias = None

# adding a name in __slots__ after class creation doesn't "work" in Python,
# but in this case it has the effect of telling the annotator that this
# attribute is allowed to be moved up to this class.
baseobjspace.W_Root.__slots__ += ('w_thunkalias',)

class W_Thunk(baseobjspace.W_Root, object):
    def __init__(w_self, w_callable, args):
        w_self.w_callable = w_callable
        w_self.args = args
        w_self.operr = None

# special marker to say that w_self has not been computed yet
w_NOT_COMPUTED_THUNK = W_Thunk(None, None)
W_Thunk.w_thunkalias = w_NOT_COMPUTED_THUNK


def _force(space, w_self):
    w_alias = w_self.w_thunkalias
    while w_alias is not None:
        if w_alias is w_NOT_COMPUTED_THUNK:
            assert isinstance(w_self, W_Thunk)
            if w_self.operr is not None:
                raise w_self.operr
            w_callable = w_self.w_callable
            args       = w_self.args
            if w_callable is None or args is None:
                raise OperationError(space.w_RuntimeError,
                                 space.wrap("thunk is already being computed"))
            w_self.w_callable = None
            w_self.args       = None
            try:
                w_alias = space.call_args(w_callable, args)
            except OperationError, operr:
                w_self.operr = operr
                raise
            # XXX detect circular w_alias result
            w_self.w_thunkalias = w_alias
        w_self = w_alias
        w_alias = w_self.w_thunkalias
    return w_self

def force(space, w_self):
    if w_self.w_thunkalias is not None:
        w_self = _force(space, w_self)
    return w_self

def thunk(w_callable, __args__):
    """thunk(f, *args, **kwds) -> an object that behaves like the
    result of the call f(*args, **kwds).  The call is performed lazily."""
    return W_Thunk(w_callable, __args__)
app_thunk = gateway.interp2app(thunk, unwrap_spec=[baseobjspace.W_Root,
                                                   argument.Arguments])

def is_thunk(space, w_obj):
    """Check if an object is a thunk that has not been computed yet."""
    return space.newbool(w_obj.w_thunkalias is w_NOT_COMPUTED_THUNK)
app_is_thunk = gateway.interp2app(is_thunk)

def become(space, w_target, w_source):
    """Globally replace the target object with the source one."""
    w_target = force(space, w_target)
    w_target.w_thunkalias = w_source
    return space.w_None
app_become = gateway.interp2app(become)

def lazy(space, w_callable):
    """Decorator to make a callable return its results wrapped in a thunk."""
    meth = Method(space, space.w_fn_thunk,
                  w_callable, space.type(w_callable))
    return space.wrap(meth)
app_lazy = gateway.interp2app(lazy)

# __________________________________________________________________________

nb_forcing_args = {}

def setup():
    nb_forcing_args.update({
        'setattr': 2,   # instead of 3
        'setitem': 2,   # instead of 3
        'get': 2,       # instead of 3
        # ---- irregular operations ----
        'wrap': 0,
        'str_w': 1,
        'int_w': 1,
        'float_w': 1,
        'uint_w': 1,
        'unichars_w': 1,
        'bigint_w': 1,
        'interpclass_w': 1,
        'unwrap': 1,
        'is_true': 1,
        'is_w': 2,
        'newtuple': 0,
        'newlist': 0,
        'newstring': 0,
        'newunicode': 0,
        'newdict': 0,
        'newslice': 0,
        'call_args': 1,
        'marshal_w': 1,
        'log': 1,
        })
    for opname, _, arity, _ in baseobjspace.ObjSpace.MethodTable:
        nb_forcing_args.setdefault(opname, arity)
    for opname in baseobjspace.ObjSpace.IrregularOpTable:
        assert opname in nb_forcing_args, "missing %r" % opname

setup()
del setup

# __________________________________________________________________________

def proxymaker(space, opname, parentfn):
    nb_args = nb_forcing_args[opname]
    if nb_args == 0:
        proxy = None
    elif nb_args == 1:
        def proxy(w1, *extra):
            w1 = force(space, w1)
            return parentfn(w1, *extra)
    elif nb_args == 2:
        def proxy(w1, w2, *extra):
            w1 = force(space, w1)
            w2 = force(space, w2)
            return parentfn(w1, w2, *extra)
    elif nb_args == 3:
        def proxy(w1, w2, w3, *extra):
            w1 = force(space, w1)
            w2 = force(space, w2)
            w3 = force(space, w3)
            return parentfn(w1, w2, w3, *extra)
    else:
        raise NotImplementedError("operation %r has arity %d" %
                                  (opname, nb_args))
    return proxy

def Space(*args, **kwds):
    # for now, always make up a wrapped StdObjSpace
    from pypy.objspace import std
    space = std.Space(*args, **kwds)
    patch_space_in_place(space, 'thunk', proxymaker)
    w___pypy__ = space.getbuiltinmodule("__pypy__")
    space.w_fn_thunk = space.wrap(app_thunk)
    space.setattr(w___pypy__, space.wrap('thunk'),
                  space.w_fn_thunk)
    space.setattr(w___pypy__, space.wrap('is_thunk'),
                  space.wrap(app_is_thunk))
    space.setattr(w___pypy__, space.wrap('become'),
                 space.wrap(app_become))
    space.setattr(w___pypy__, space.wrap('lazy'),
                 space.wrap(app_lazy))
    return space
