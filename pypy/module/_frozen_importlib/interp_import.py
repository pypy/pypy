from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import SpaceCache


class FrozenCache(SpaceCache):
    def __init__(self, space):
        mod = space.getbuiltinmodule('_frozen_importlib')
        self.w_frozen_import = mod.get('__import__')
        assert self.w_frozen_import is not None

class FastPathGiveUp(Exception):
    pass

def _gcd_import(space, name):
    # check sys.modules, if the module is already there and initialized, we can
    # use it, otherwise fall back to importlib.__import__

    # NB: we don't get the importing lock here, but CPython has the same fast
    # path
    w_modules = space.sys.get('modules')
    w_module = space.finditem_str(w_modules, name)
    if w_module is None:
        raise FastPathGiveUp

    # to check whether a module is initialized, we can ask for
    # module.__spec__._initializing, which should be False
    try:
        w_spec = space.getattr(w_module, space.newtext("__spec__"))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise
        raise FastPathGiveUp
    try:
        w_initializing = space.getattr(w_spec, space.newtext("_initializing"))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise
        # we have no mod.__spec__._initializing, so it's probably a builtin
        # module which we can assume is initialized
    else:
        if space.is_true(w_initializing):
            raise FastPathGiveUp
    return w_module


@unwrap_spec(w_globals=WrappedDefault(None), w_locals=WrappedDefault(None), w_fromlist=WrappedDefault(()),
             w_level=WrappedDefault(0))
def interp___import__(space, w_name, w_globals, w_locals, w_fromlist,
        w_level):
    """
    Import a module. Because this function is meant for use by the Python
    interpreter and not for general use, it is better to use
    importlib.import_module() to programmatically import a module.
    
    The globals argument is only used to determine the context;
    they are not modified.  The locals argument is unused.  The fromlist
    should be a list of names to emulate ``from name import ...'', or an
    empty list to emulate ``import name''.
    When importing a module from a package, note that __import__('A.B', ...)
    returns package A when fromlist is empty, but its submodule B when
    fromlist is not empty.  The level argument is used to determine whether to
    perform absolute or relative imports: 0 is absolute, while a positive number
    is the number of parent directories to search relative to the current module."""
    level = space.int_w(w_level)
    if level == 0:
        # fast path only for absolute imports without a "from" list, for now
        # fromlist can be supported if we are importing from a module, not a
        # package. to check that, look for the existence of __path__ attribute
        # in w_mod
        try:
            name = space.text_w(w_name)
            w_mod = _gcd_import(space, name)
            have_fromlist = space.is_true(w_fromlist)
            if not have_fromlist:
                dotindex = name.find(".")
                if dotindex < 0:
                    return w_mod
                return _gcd_import(space, name[:dotindex])
        except FastPathGiveUp:
            pass
        else:
            assert have_fromlist
            w_path = space.findattr(w_mod, space.newtext("__path__"))
            if w_path is not None:
                # hard case, a package! Call back into importlib
                w_importlib = space.getbuiltinmodule('_frozen_importlib')
                return space.call_method(w_importlib, "_handle_fromlist",
                        w_mod, w_fromlist,
                        space.w_default_importlib_import)
            else:
                return w_mod
    try:
        return space.call_function(
            space.fromcache(FrozenCache).w_frozen_import, w_name, w_globals, w_locals, w_fromlist,
                    w_level)
    except OperationError as e:
        e.remove_traceback_module_frames(
              '<frozen importlib._bootstrap>',
              '<frozen importlib._bootstrap_external>',
              '<builtin>/frozen importlib._bootstrap_external')
        raise
interp___import__ = interp2app(interp___import__,
                                        app_name='__import__')
