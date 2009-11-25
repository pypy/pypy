import py
from pypy.jit.backend.cli.runner import CliCPU
from pypy.jit.backend.test.runner_test import OOtypeBackendTest

class FakeStats(object):
    pass

# ____________________________________________________________

class CliJitMixin(object):

    typesystem = 'ootype'
    CPUClass = CliCPU

    # for the individual tests see
    # ====> ../../test/runner_test.py
    
    def setup_class(cls):
        cls.cpu = cls.CPUClass(rtyper=None, stats=FakeStats())


class TestRunner(CliJitMixin, OOtypeBackendTest):
    avoid_instances = True
    
    def skip(self):
        py.test.skip("not supported in non-translated version")

    test_passing_guard_class = skip      # GUARD_CLASS
    test_failing_guard_class = skip      # GUARD_CLASS
    test_call = skip
    test_field = skip
    test_field_basic = skip
    test_ooops = skip
    test_jump = skip

    def test_unused_result_float(self):
        py.test.skip('fixme! max 32 inputargs so far')

    def test_ovf_operations(self, reversed=False):
        self.skip()

    def test_do_unicode_basic(self):
        py.test.skip('fixme!')

    def test_unicode_basic(self):
        py.test.skip('fixme!')

    def test_backends_dont_keep_loops_alive(self):
        pass # the cli backend DOES keep loops alive

def test_pypycliopt():
    import os
    from pypy.jit.backend.cli.method import Method
    
    def getmeth(value):
        oldenv = os.environ.get('PYPYJITOPT')
        os.environ['PYPYJITOPT'] = value
        meth = Method.__new__(Method) # evil hack not to call __init__
        meth.setoptions()
        if oldenv:
            os.environ['PYPYJITOPT'] = oldenv
        else:
            del os.environ['PYPYJITOPT']
        return meth

    meth = getmeth('')
    assert meth.debug == Method.debug
    assert meth.tailcall == Method.tailcall

    meth = getmeth('debug -tailcall')
    assert meth.debug
    assert not meth.tailcall

    meth = getmeth('+debug +tailcall')
    assert meth.debug
    assert meth.tailcall
