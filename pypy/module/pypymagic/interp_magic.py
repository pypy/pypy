from pypy.interpreter.error import OperationError
from pypy.rlib.objectmodel import we_are_translated

def pypy_repr(space, w_object):
    return space.wrap('%r' % (w_object,))

def isfake(space, w_obj):
    if we_are_translated():
        return space.w_False
    return space.wrap(bool(w_obj.typedef.fakedcpytype))
    #return space.wrap(bool(getattr(w_obj.typedef, 'fakedcpytype', None)))

def interp_pdb(space):
    """Run an interp-level pdb.
    This is not available in translated versions of PyPy."""
    if we_are_translated():
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("Cannot use interp-level pdb in translated pypy"))
    else:
        import pdb
        pdb.set_trace()
