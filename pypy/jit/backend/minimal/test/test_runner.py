import py
from pypy.jit.backend.minimal.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.backend.test.runner_test import LLtypeBackendTest
from pypy.jit.backend.test.runner_test import OOtypeBackendTest

class FakeStats(object):
    pass

# ____________________________________________________________

class MinimalTestMixin(object):

    # for the individual tests see
    # ====> ../../test/runner.py
    
    def setup_class(cls):
        cls.cpu = cls.CPUClass(rtyper=None, stats=FakeStats())

    def _skip(self):
        py.test.skip("not supported in non-translated version")

    test_passing_guards      = _skip      # GUARD_CLASS
    test_passing_guard_class = _skip      # GUARD_CLASS
    test_failing_guards      = _skip      # GUARD_CLASS
    test_failing_guard_class = _skip      # GUARD_CLASS
    test_ovf_operations_reversed = _skip  # exception

class TestOOtype(OOJitMixin, MinimalTestMixin, OOtypeBackendTest):
    pass

class TestLLtype(LLJitMixin, MinimalTestMixin, LLtypeBackendTest):
    pass

