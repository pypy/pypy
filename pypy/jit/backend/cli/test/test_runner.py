import py
from pypy.jit.backend.cli.runner import CliCPU
from pypy.jit.backend.test.runner import OOtypeBackendTest

class FakeStats(object):
    pass

# ____________________________________________________________

class CliJitMixin(object):

    typesystem = 'ootype'
    CPUClass = CliCPU

    # for the individual tests see
    # ====> ../../test/runner.py
    
    def setup_class(cls):
        cls.cpu = cls.CPUClass(rtyper=None, stats=FakeStats())

    def _skip(self):
        py.test.skip("not supported in non-translated version")

    test_passing_guard_class = _skip      # GUARD_CLASS
    test_failing_guard_class = _skip      # GUARD_CLASS


class TestRunner(CliJitMixin, OOtypeBackendTest):
    pass
