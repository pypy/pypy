from pypy.rlib.debug import debug_print
from pypy.rlib import rstm
from pypy.translator.stm.test.support import CompiledSTMTests

def test_stm_perform_transaction():
    class Arg(object):
        _alloc_nonmovable_ = True

    def setx(arg):
        arg.x = 42

    arg = Arg()
    rstm.descriptor_init()
    rstm.perform_transaction(setx, Arg, arg)
    rstm.descriptor_done()
    assert arg.x == 42


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
