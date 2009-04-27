import py
from pypy.jit.backend.minimal.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.backend.test.runner import BaseBackendTest

class FakeStats(object):
    pass

# ____________________________________________________________

class MinimalTest(BaseBackendTest):

    # for the individual tests see
    # ====> ../../test/runner.py
    
    def setup_class(cls):
        cls.cpu = cls.CPUClass(rtyper=None, stats=FakeStats())

    def _skip(self):
        py.test.skip("not supported in non-translated version")

    test_passing_guards = _skip      # GUARD_CLASS
    test_failing_guards = _skip      # GUARD_CLASS


## class TestOOtype(OOJitMixin, MinimalTest):
##     pass

class TestLLtype(LLJitMixin, MinimalTest):
    pass

