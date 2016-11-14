from pypy.interpreter.error import OperationError, oefmt, wrap_oserror
from pypy.interpreter.gateway import WrappedDefault, unwrap_spec
from pypy.interpreter.pycode import CodeHookCache
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.mixedmodule import MixedModule
from rpython.rlib.objectmodel import we_are_translated
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.setobject import W_BaseSetObject
from pypy.objspace.std.typeobject import MethodCache
from pypy.objspace.std.mapdict import MapAttrCache
from rpython.rlib import rposix, rgc


def internal_repr(space, w_object):
    return space.wrap('%r' % (w_object,))


def attach_gdb(space):
    """Run an interp-level gdb (or pdb when untranslated)"""
    from rpython.rlib.debug import attach_gdb
    attach_gdb()


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
    cache = space.fromcache(MapAttrCache)
    cache.misses = {}
    cache.hits = {}

@unwrap_spec(name=str)
def mapdict_cache_counter(space, name):
    """Return a tuple (index_cache_hits, index_cache_misses) for lookups
    in the mapdict cache with the given attribute name."""
    assert space.config.objspace.std.withmethodcachecounter
    cache = space.fromcache(MapAttrCache)
    return space.newtuple([space.newint(cache.hits.get(name, 0)),
                           space.newint(cache.misses.get(name, 0))])

def builtinify(space, w_func):
    """To implement at app-level modules that are, in CPython,
    implemented in C: this decorator protects a function from being ever
    bound like a method.  Useful because some tests do things like put
    a "built-in" function on a class and access it via the instance.
    """
    from pypy.interpreter.function import Function, BuiltinFunction
    func = space.interp_w(Function, w_func)
    bltn = BuiltinFunction(func)
    return space.wrap(bltn)

def hidden_applevel(space, w_func):
    """Decorator that hides a function's frame from app-level"""
    from pypy.interpreter.function import Function
    func = space.interp_w(Function, w_func)
    func.getcode().hidden_applevel = True
    return w_func

@unwrap_spec(meth=str)
def lookup_special(space, w_obj, meth):
    """Lookup up a special method on an object."""
    w_descr = space.lookup(w_obj, meth)
    if w_descr is None:
        return space.w_None
    return space.get(w_descr, w_obj)

def do_what_I_mean(space, w_crash=None):
    if not space.is_none(w_crash):
        raise ValueError    # RPython-level, uncaught
    return space.wrap(42)


def strategy(space, w_obj):
    """ strategy(dict or list or set)

    Return the underlying strategy currently used by a dict, list or set object
    """
    if isinstance(w_obj, W_DictMultiObject):
        name = w_obj.get_strategy().__class__.__name__
    elif isinstance(w_obj, W_ListObject):
        name = w_obj.strategy.__class__.__name__
    elif isinstance(w_obj, W_BaseSetObject):
        name = w_obj.strategy.__class__.__name__
    else:
        raise oefmt(space.w_TypeError, "expecting dict or list or set object")
    return space.wrap(name)


@unwrap_spec(fd='c_int')
def validate_fd(space, fd):
    try:
        rposix.validate_fd(fd)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(sizehint=int)
def resizelist_hint(space, w_iterable, sizehint):
    if not isinstance(w_iterable, W_ListObject):
        raise oefmt(space.w_TypeError, "arg 1 must be a 'list'")
    w_iterable._resize_hint(sizehint)

@unwrap_spec(sizehint=int)
def newlist_hint(space, sizehint):
    return space.newlist_hint(sizehint)

@unwrap_spec(debug=int)
def set_debug(space, debug):
    debug = bool(debug)
    space.sys.debug = debug
    space.setitem(space.builtin.w_dict,
                  space.wrap('__debug__'),
                  space.wrap(debug))

@unwrap_spec(estimate=int)
def add_memory_pressure(estimate):
    rgc.add_memory_pressure(estimate)

@unwrap_spec(w_frame=PyFrame)
def locals_to_fast(space, w_frame):
    assert isinstance(w_frame, PyFrame)
    w_frame.locals2fast()

@unwrap_spec(w_module=MixedModule)
def save_module_content_for_future_reload(space, w_module):
    w_module.save_module_content_for_future_reload()

def set_code_callback(space, w_callable):
    cache = space.fromcache(CodeHookCache)
    if space.is_none(w_callable):
        cache._code_hook = None
    else:
        cache._code_hook = w_callable

@unwrap_spec(string=str, byteorder=str, signed=int)
def decode_long(space, string, byteorder='little', signed=1):
    from rpython.rlib.rbigint import rbigint, InvalidEndiannessError
    try:
        result = rbigint.frombytes(string, byteorder, bool(signed))
    except InvalidEndiannessError:
        raise oefmt(space.w_ValueError, "invalid byteorder argument")
    return space.newlong_from_rbigint(result)

def _promote(space, w_obj):
    """ Promote the first argument of the function and return it. Promote is by
    value for ints, floats, strs, unicodes (but not subclasses thereof) and by
    reference otherwise.  (Unicodes not supported right now.)

    This function is experimental!"""
    from rpython.rlib import jit
    if space.is_w(space.type(w_obj), space.w_int):
        jit.promote(space.int_w(w_obj))
    elif space.is_w(space.type(w_obj), space.w_float):
        jit.promote(space.float_w(w_obj))
    elif space.is_w(space.type(w_obj), space.w_str):
        jit.promote_string(space.str_w(w_obj))
    elif space.is_w(space.type(w_obj), space.w_unicode):
        raise oefmt(space.w_TypeError, "promoting unicode unsupported")
    else:
        jit.promote(w_obj)
    return w_obj

@unwrap_spec(w_value=WrappedDefault(None), w_tb=WrappedDefault(None))
def normalize_exc(space, w_type, w_value=None, w_tb=None):
    operr = OperationError(w_type, w_value, w_tb)
    operr.normalize_exception(space)
    return operr.get_w_value(space)
