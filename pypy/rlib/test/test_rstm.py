from pypy.rlib.debug import debug_print
from pypy.rlib import rstm
from pypy.translator.c.test.test_standalone import StandaloneTests

def test_stm_perform_transaction():
    class Arg(object):
        _alloc_nonmovable_ = True

    def setx(arg):
        arg.x = 42

    arg = Arg()
    rstm.stm_descriptor_init()
    rstm.stm_perform_transaction(setx, Arg, arg)
    rstm.stm_descriptor_done()
    assert arg.x == 42


class CompiledSTMTests(StandaloneTests):
    gc = "none"

    def compile(self, entry_point):
        from pypy.config.pypyoption import get_pypy_config
        self.config = get_pypy_config(translating=True)
        self.config.translation.stm = True
        self.config.translation.gc = self.gc
        #
        # Prevent the RaiseAnalyzer from just emitting "WARNING: Unknown
        # operation".  We want instead it to crash.
        from pypy.translator.backendopt.canraise import RaiseAnalyzer
        RaiseAnalyzer.fail_on_unknown_operation = True
        try:
            res = StandaloneTests.compile(self, entry_point, debug=True)
        finally:
            RaiseAnalyzer.fail_on_unknown_operation = False
        return res


class TestTransformSingleThread(CompiledSTMTests):

    def test_no_pointer_operations(self):
        def simplefunc(argv):
            i = 0
            while i < 100:
                i += 3
            debug_print(i)
            return 0
        t, cbuilder = self.compile(simplefunc)
        dataout, dataerr = cbuilder.cmdexec('', err=True)
        assert dataout == ''
        assert '102' in dataerr.splitlines()
