from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module provides the components needed to build your own
    __import__ function.
    """
    interpleveldefs = {
        'PY_SOURCE':       'space.wrap(importing.PY_SOURCE)',
        'PY_COMPILED':     'space.wrap(importing.PY_COMPILED)',
        'C_EXTENSION':     'space.wrap(importing.C_EXTENSION)',
        'PKG_DIRECTORY':   'space.wrap(importing.PKG_DIRECTORY)',
        'C_BUILTIN':       'space.wrap(importing.C_BUILTIN)',
        'PY_FROZEN':       'space.wrap(importing.PY_FROZEN)',
        'get_suffixes':    'interp_imp.get_suffixes',

        'get_magic':       'interp_imp.get_magic',
        'find_module':     'interp_imp.find_module',
        'load_module':     'interp_imp.load_module',
        'load_source':     'interp_imp.load_source',
        'load_compiled':   'interp_imp.load_compiled',
        #'run_module':      'interp_imp.run_module',
        'new_module':      'interp_imp.new_module',
        'init_builtin':    'interp_imp.init_builtin',
        'init_frozen':     'interp_imp.init_frozen',
        'is_builtin':      'interp_imp.is_builtin',
        'is_frozen':       'interp_imp.is_frozen',

        'lock_held':       'interp_imp.lock_held',
        'acquire_lock':    'interp_imp.acquire_lock',
        'release_lock':    'interp_imp.release_lock',
        }

    appleveldefs = {
        }
