import py
from pypy.interpreter.baseobjspace import ObjSpace

# __________________________________________________________________________

def get_operations():
    return [r[0] for r in ObjSpace.MethodTable] + ObjSpace.IrregularOpTable

def create_proxy_space(proxyname, proxymaker, operations=None, space=None):
    """ Will create a proxy object space if no space supplied.  Otherwise
    will patch the supplied space."""

    if space is None:
        # make up a StdObjSpace by default
        from pypy.objspace import std
        space = std.Space()

    if operations is None:
        operations = get_operations()

    for name in operations:
        parentfn = getattr(space, name)
        proxy = proxymaker(space, name, parentfn)
        if proxy:
            setattr(space, name, proxy)

    prevrepr = space.__repr__()
    space.__repr__ = lambda: '%s(%s)' % (proxyname, prevrepr)

    return space

# __________________________________________________________________________
