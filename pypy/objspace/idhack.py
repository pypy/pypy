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
from pypy.interpreter import gateway

# ____________________________________________________________

def canonical(w_obj):
    try:
        return w_obj.__unified_with[-1]
    except AttributeError:
        return w_obj

def become(space, w_target, w_source):
    try:
        targetfamily = w_target.__unified_with
    except AttributeError:
        targetfamily = [w_target]
    w_source.__unified_with = targetfamily
    targetfamily.append(w_source)
    for w_obj in targetfamily:
        w_obj.__class__ = w_source.__class__
        w_obj.__dict__  = w_source.__dict__
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
