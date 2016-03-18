from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module provides the components needed to build your own
    __import__ function.
    """
    applevel_name = '_imp'

    interpleveldefs = {
        'SEARCH_ERROR':    'space.wrap(importing.SEARCH_ERROR)',
        'PY_SOURCE':       'space.wrap(importing.PY_SOURCE)',
        'PY_COMPILED':     'space.wrap(importing.PY_COMPILED)',
        'C_EXTENSION':     'space.wrap(importing.C_EXTENSION)',
        'PKG_DIRECTORY':   'space.wrap(importing.PKG_DIRECTORY)',
        'C_BUILTIN':       'space.wrap(importing.C_BUILTIN)',
        'PY_FROZEN':       'space.wrap(importing.PY_FROZEN)',
        'IMP_HOOK':        'space.wrap(importing.IMP_HOOK)',
        'get_suffixes':    'interp_imp.get_suffixes',
        'extension_suffixes': 'interp_imp.extension_suffixes',

        'get_magic':       'interp_imp.get_magic',
        'get_tag':         'interp_imp.get_tag',
        'load_dynamic':    'interp_imp.load_dynamic',
        'new_module':      'interp_imp.new_module',
        'init_builtin':    'interp_imp.init_builtin',
        'init_frozen':     'interp_imp.init_frozen',
        'is_builtin':      'interp_imp.is_builtin',
        'is_frozen':       'interp_imp.is_frozen',
        'get_frozen_object': 'interp_imp.get_frozen_object',
        'is_frozen_package': 'interp_imp.is_frozen_package',
        'NullImporter':    'importing.W_NullImporter',

        'lock_held':       'interp_imp.lock_held',
        'acquire_lock':    'interp_imp.acquire_lock',
        'release_lock':    'interp_imp.release_lock',

        'cache_from_source': 'interp_imp.cache_from_source',
        'source_from_cache': 'interp_imp.source_from_cache',
        '_fix_co_filename': 'interp_imp.fix_co_filename',
        }

    appleveldefs = {
        }

    def __init__(self, space, *args):
        "NOT_RPYTHON"
        MixedModule.__init__(self, space, *args)
        from pypy.module.posix.interp_posix import add_fork_hook
        from pypy.module.imp import interp_imp
        add_fork_hook('before', interp_imp.acquire_lock)
        add_fork_hook('parent', interp_imp.release_lock)
        add_fork_hook('child', interp_imp.reinit_lock)
