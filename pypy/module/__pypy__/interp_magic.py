from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.gateway import unwrap_spec
from pypy.rlib.objectmodel import we_are_translated
from pypy.objspace.std.typeobject import MethodCache
from pypy.objspace.std.mapdict import IndexCache


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

@unwrap_spec(name=str)
def method_cache_counter(space, name):
    """Return a tuple (method_cache_hits, method_cache_misses) for calls to
    methods with the name."""
    assert space.config.objspace.std.withmethodcachecounter
    cache = space.fromcache(MethodCache)
    return space.newtuple([space.newint(cache.hits.get(name, 0)),
                           space.newint(cache.misses.get(name, 0))])

def reset_method_cache_counter(space):
    """Reset the method cache counter to zero for all method names."""
    assert space.config.objspace.std.withmethodcachecounter
    cache = space.fromcache(MethodCache)
    cache.misses = {}
    cache.hits = {}
    if space.config.objspace.std.withmapdict:
        cache = space.fromcache(IndexCache)
        cache.misses = {}
        cache.hits = {}

@unwrap_spec(name=str)
def mapdict_cache_counter(space, name):
    """Return a tuple (index_cache_hits, index_cache_misses) for lookups
    in the mapdict cache with the given attribute name."""
    assert space.config.objspace.std.withmethodcachecounter
    assert space.config.objspace.std.withmapdict
    cache = space.fromcache(IndexCache)
    return space.newtuple([space.newint(cache.hits.get(name, 0)),
                           space.newint(cache.misses.get(name, 0))])

def builtinify(space, w_func):
    from pypy.interpreter.function import Function, BuiltinFunction
    func = space.interp_w(Function, w_func)
    bltn = BuiltinFunction(func)
    return space.wrap(bltn)

@unwrap_spec(ObjSpace, W_Root, str)
def lookup_special(space, w_obj, meth):
    """Lookup up a special method on an object."""
    w_descr = space.lookup(w_obj, meth)
    if w_descr is None:
        return space.w_None
    return space.get(w_descr, w_obj)
