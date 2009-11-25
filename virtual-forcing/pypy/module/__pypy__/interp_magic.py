from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace
from pypy.rlib.objectmodel import we_are_translated

def internal_repr(space, w_object):
    return space.wrap('%r' % (w_object,))

def isfake(space, w_obj):
    """Return whether the argument is faked (stolen from CPython). This is
    always False after translation."""
    if we_are_translated():
        return space.w_False
    return space.wrap(bool(w_obj.typedef.fakedcpytype))
    #return space.wrap(bool(getattr(w_obj.typedef, 'fakedcpytype', None)))

def interp_pdb(space):
    """Run an interp-level pdb.
    This is not available in translated versions of PyPy."""
    assert not we_are_translated()
    import pdb
    pdb.set_trace()

def method_cache_counter(space, name):
    """Return a tuple (method_cache_hits, method_cache_misses) for calls to
    methods with the name."""
    assert space.config.objspace.std.withmethodcachecounter
    return space.newtuple([space.newint(space.method_cache_hits.get(name, 0)),
                           space.newint(space.method_cache_misses.get(name, 0)),])
method_cache_counter.unwrap_spec = [ObjSpace, str]

def reset_method_cache_counter(space):
    """Reset the method cache counter to zero for all method names."""
    assert space.config.objspace.std.withmethodcachecounter
    space.method_cache_misses = {}
    space.method_cache_hits = {}

