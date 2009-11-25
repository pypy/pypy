from pypy.interpreter.baseobjspace import ObjSpace

# __________________________________________________________________________

def get_operations():
    return [r[0] for r in ObjSpace.MethodTable] + ObjSpace.IrregularOpTable

def patch_space_in_place(space, proxyname, proxymaker, operations=None):
    """Patches the supplied space."""

    if operations is None:
        operations = get_operations()

    for name in operations:
        parentfn = getattr(space, name)
        proxy = proxymaker(space, name, parentfn)
        if proxy:
            setattr(space, name, proxy)

    prevrepr = repr(space)
    space._this_space_repr_ = '%s(%s)' % (proxyname, prevrepr)

# __________________________________________________________________________
