import py
from pypy.jit.backend.minimal.runner import LLtypeCPU, OOtypeCPU
from pypy.jit.backend.test.runner import BaseBackendTest

class FakeStats(object):
    pass

# ____________________________________________________________

class TestMinimal(BaseBackendTest):

    # for the individual tests see
    # ====> ../../test/runner.py
    
    def setup_class(cls):
        cls.cpu = LLtypeCPU(rtyper=None, stats=FakeStats())

    def _skip(self):
        py.test.skip("not supported in non-translated version")

    test_passing_guards = _skip      # GUARD_CLASS
    test_failing_guards = _skip      # GUARD_CLASS
