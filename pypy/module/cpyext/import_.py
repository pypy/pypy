from pypy.interpreter import module
from pypy.module.cpyext.api import (
    generic_cpy_call, cpython_api, PyObject, CONST_STRING)
from pypy.rpython.lltypesystem import rffi
from pypy.interpreter.error import OperationError

@cpython_api([PyObject], PyObject)
def PyImport_Import(space, w_name):
    """
    This is a higher-level interface that calls the current "import hook function".
    It invokes the __import__() function from the __builtins__ of the
    current globals.  This means that the import is done using whatever import hooks
    are installed in the current environment, e.g. by rexec or ihooks.

    Always uses absolute imports."""
    caller = space.getexecutioncontext().gettopframe_nohidden()
    # Get the builtins from current globals
    if caller is not None:
        w_globals = caller.w_globals
        w_builtin = space.getitem(w_globals, space.wrap('__builtins__'))
    else:
        # No globals -- use standard builtins, and fake globals
        w_builtin = space.getbuiltinmodule('__builtin__')
        w_globals = space.newdict()
        space.setitem(w_globals, space.wrap("__builtins__"), w_builtin)

    # Get the __import__ function from the builtins
    if space.is_true(space.isinstance(w_builtin, space.w_dict)):
        w_import = space.getitem(w_builtin, space.wrap("__import__"))
    else:
        w_import = space.getattr(w_builtin, space.wrap("__import__"))

    # Call the __import__ function with the proper argument list
    # Always use absolute import here.
    return space.call_function(w_import,
                               w_name, w_globals, w_globals,
                               space.newlist([space.wrap("__doc__")]))

@cpython_api([CONST_STRING], PyObject)
def PyImport_ImportModule(space, name):
    return PyImport_Import(space, space.wrap(rffi.charp2str(name)))

@cpython_api([CONST_STRING], PyObject)
def PyImport_ImportModuleNoBlock(space, name):
    space.warn('PyImport_ImportModuleNoBlock() is not non-blocking',
               space.w_RuntimeWarning)
    return PyImport_Import(space, space.wrap(rffi.charp2str(name)))

@cpython_api([PyObject], PyObject)
def PyImport_ReloadModule(space, w_mod):
    from pypy.module.imp.importing import reload
    return reload(space, w_mod)

