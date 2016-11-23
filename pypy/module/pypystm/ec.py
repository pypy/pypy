"""
Attach extra STM-only attributes to the ExecutionContext.
"""

from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.gateway import W_Root


class FakeWeakKeyDictionary:
    # Only used if we don't have weakrefs.
    # Then thread._local instances will leak, but too bad.
    def __init__(self):
        self.d = {}
    def get(self, key):
        return self.d.get(key, None)
    def set(self, key, value):
        self.d[key] = value

def initialize_execution_context(ec):
    """Called from ExecutionContext.__init__()."""
    if ec.space.config.translation.rweakref:
        from rpython.rlib import rweakref
        from pypy.module.pypystm.local import STMLocal
        ec._thread_local_dicts = rweakref.RWeakKeyDictionary(STMLocal, W_Root)
    else:
        ec._thread_local_dicts = FakeWeakKeyDictionary()
    from pypy.objspace.std.typeobject import MethodCache
    ec._methodcache = MethodCache(ec.space)
