"""Example usage:

    $ python interpreter/py.py -o thunk
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
"""

from proxy import create_proxy_space
from pypy.interpreter import gateway, baseobjspace, argument

# __________________________________________________________________________

class W_Thunk(baseobjspace.W_Root, object):
    def __init__(w_self, space, w_callable, args=argument.Arguments([])):
        w_self.space = space
        w_self.w_callable = w_callable
        w_self.args = args
        w_self.w_value = None

def force(w_self):
    while isinstance(w_self, W_Thunk):
        if w_self.w_value is None:
            w_self.w_value = w_self.space.call_args(w_self.w_callable,
                                                    w_self.args)
            w_self.w_callable = None
            w_self.args = None
        w_self = w_self.w_value
    return w_self

def thunk(space, w_callable, __args__):
    return W_Thunk(space, w_callable, __args__)
app_thunk = gateway.interp2app(thunk, unwrap_spec=[baseobjspace.ObjSpace,
                                                   baseobjspace.W_Root,
                                                   argument.Arguments])

# __________________________________________________________________________

operation_args_that_dont_force = {
    ('setattr', 2): True,
    ('setitem', 2): True,
    }

def proxymaker(space, opname, parentfn):
    def proxy(*args):
        newargs = []
        for i in range(len(args)):
            a = args[i]
            if (opname, i) not in operation_args_that_dont_force:
                a = force(a)
            newargs.append(a)
        return parentfn(*newargs)
    return proxy

def Space():
    space = create_proxy_space('thunk', proxymaker)
    space.setitem(space.builtin.w_dict, space.wrap('thunk'),
                  space.wrap(app_thunk))
    return space
