from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import unwrap_spec
from rpython.rlib.objectmodel import we_are_translated
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.typeobject import MethodCache
from pypy.objspace.std.mapdict import MapAttrCache
from rpython.rlib import rposix, rgc


def internal_repr(space, w_object):
    return space.wrap('%r' % (w_object,))


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
        cache = space.fromcache(MapAttrCache)
        cache.misses = {}
        cache.hits = {}

@unwrap_spec(name=str)
def mapdict_cache_counter(space, name):
    """Return a tuple (index_cache_hits, index_cache_misses) for lookups
    in the mapdict cache with the given attribute name."""
    assert space.config.objspace.std.withmethodcachecounter
    assert space.config.objspace.std.withmapdict
    cache = space.fromcache(MapAttrCache)
    return space.newtuple([space.newint(cache.hits.get(name, 0)),
                           space.newint(cache.misses.get(name, 0))])

def builtinify(space, w_func):
    from pypy.interpreter.function import Function, BuiltinFunction
    func = space.interp_w(Function, w_func)
    bltn = BuiltinFunction(func)
    return space.wrap(bltn)

@unwrap_spec(meth=str)
def lookup_special(space, w_obj, meth):
    """Lookup up a special method on an object."""
    if space.is_oldstyle_instance(w_obj):
        w_msg = space.wrap("this doesn't do what you want on old-style classes")
        raise OperationError(space.w_TypeError, w_msg)
    w_descr = space.lookup(w_obj, meth)
    if w_descr is None:
        return space.w_None
    return space.get(w_descr, w_obj)

def do_what_I_mean(space):
    return space.wrap(42)

def list_strategy(space, w_list):
    if isinstance(w_list, W_ListObject):
        return space.wrap(w_list.strategy._applevel_repr)
    else:
        w_msg = space.wrap("Can only get the list strategy of a list")
        raise OperationError(space.w_TypeError, w_msg)

@unwrap_spec(fd='c_int')
def validate_fd(space, fd):
    try:
        rposix.validate_fd(fd)
    except OSError, e:
        raise wrap_oserror(space, e)

def get_console_cp(space):
    from rpython.rlib import rwin32    # Windows only
    return space.newtuple([
        space.wrap('cp%d' % rwin32.GetConsoleCP()),
        space.wrap('cp%d' % rwin32.GetConsoleOutputCP()),
        ])

@unwrap_spec(sizehint=int)
def resizelist_hint(space, w_iterable, sizehint):
    if not isinstance(w_iterable, W_ListObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("arg 1 must be a 'list'"))
    w_iterable._resize_hint(sizehint)

@unwrap_spec(sizehint=int)
def newlist_hint(space, sizehint):
    return space.newlist_hint(sizehint)

@unwrap_spec(debug=bool)
def set_debug(space, debug):
    space.sys.debug = debug
    space.setitem(space.builtin.w_dict,
                  space.wrap('__debug__'),
                  space.wrap(debug))

@unwrap_spec(estimate=int)
def add_memory_pressure(estimate):
    rgc.add_memory_pressure(estimate)
