from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace
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

def method_cache_counter(space, name):
    if not space.config.objspace.std.withmethodcachecounter:
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("not implemented"))
    ec = space.getexecutioncontext()
    return space.newtuple([space.newint(ec.method_cache_hits.get(name, 0)),
                           space.newint(ec.method_cache_misses.get(name, 0)),])
method_cache_counter.unwrap_spec = [ObjSpace, str]

def reset_method_cache_counter(space):
    if not space.config.objspace.std.withmethodcachecounter:
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("not implemented"))
    ec = space.getexecutioncontext()
    ec.method_cache_misses = {}
    ec.method_cache_hits = {}

