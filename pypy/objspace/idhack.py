"""Example usage:

    $ python interpreter/py.py -o idhack
    >>> x = 6
    >>> id(x)
    12345678
    >>> become(x, 7)
    >>> x
    7
    >>> id(x)
    12345678

"""

from proxy import create_proxy_space
from pypy.interpreter import gateway, baseobjspace

# ____________________________________________________________

class W_Dead(baseobjspace.W_Root, object):
    pass

def canonical(w_obj):
    while isinstance(w_obj, W_Dead):
        w_obj = w_obj.__pointer
    return w_obj

def become(space, w_target, w_source):
    w_target = canonical(w_target)
    w_target.__class__ = W_Dead
    w_target.__pointer = w_source
    return space.w_None
app_become = gateway.interp2app(become)

# ____________________________________________________________

def proxymaker(space, opname, parentfn):
    if opname == 'id':
        def proxy(w_obj):
            return parentfn(canonical(w_obj))
    elif opname == 'is_':
        def proxy(w_a, w_b):
            return parentfn(canonical(w_a), canonical(w_b))
    else:
        proxy = parentfn
    return proxy

def Space(space=None):
    space = create_proxy_space('idhack', proxymaker, space=space)
    space.setitem(space.builtin.w_dict, space.wrap('become'),
                 space.wrap(app_become))
    return space
