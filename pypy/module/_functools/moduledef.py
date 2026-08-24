from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    """Native lru_cache wrapper, used by lib-python/3/functools.py in
    preference to its pure-Python fallback when available.
    """

    interpleveldefs = {
        '_lru_cache_wrapper': 'interp_functools.lru_cache_wrapper',
    }

    appleveldefs = {
    }
