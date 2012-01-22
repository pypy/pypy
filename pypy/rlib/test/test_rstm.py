import os, thread, time
from pypy.rlib.debug import debug_print
from pypy.rlib import rstm
from pypy.translator.stm.test.support import CompiledSTMTests


class Arg(object):
    _alloc_nonmovable_ = True

def setx(arg, retry_counter):
    debug_print(arg.x)
    assert rstm.debug_get_state() == 1
    if arg.x == 303:
        # this will trigger stm_become_inevitable()
        os.write(1, "hello\n")
        assert rstm.debug_get_state() == 2
    arg.x = 42


def test_stm_perform_transaction(initial_x=202):
    arg = Arg()
    arg.x = initial_x
    assert rstm.debug_get_state() == -1
    rstm.descriptor_init()
    assert rstm.debug_get_state() == 0
    rstm.perform_transaction(setx, Arg, arg)
    assert rstm.debug_get_state() == 0
    rstm.descriptor_done()
    assert rstm.debug_get_state() == -1
    assert arg.x == 42

def test_stm_multiple_threads():
    ok = []
    def f(i):
        test_stm_perform_transaction()
        ok.append(i)
    for i in range(10):
        thread.start_new_thread(f, (i,))
    timeout = 10
    while len(ok) < 10:
        time.sleep(0.1)
        timeout -= 0.1
        assert timeout >= 0.0, "timeout!"
    assert sorted(ok) == range(10)


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

    def test_perform_transaction(self):
        def f(argv):
            test_stm_perform_transaction()
            return 0
        t, cbuilder = self.compile(f)
        dataout, dataerr = cbuilder.cmdexec('', err=True)
        assert dataout == ''
        assert '202' in dataerr.splitlines()

    def test_perform_transaction_inevitable(self):
        def f(argv):
            test_stm_perform_transaction(303)
            return 0
        t, cbuilder = self.compile(f)
        dataout, dataerr = cbuilder.cmdexec('', err=True)
        assert 'hello' in dataout.splitlines()
        assert '303' in dataerr.splitlines()
