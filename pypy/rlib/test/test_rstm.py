import os, thread, time
from pypy.rlib.debug import debug_print, ll_assert
from pypy.rlib import rstm
from pypy.translator.stm.test.support import CompiledSTMTests


class Arg(object):
    pass
arg = Arg()

def setx(arg, retry_counter):
    debug_print(arg.x)
    assert rstm._debug_get_state() == 1
    if arg.x == 303:
        # this will trigger stm_become_inevitable()
        os.write(1, "hello\n")
        assert rstm._debug_get_state() == 2
    arg.x = 42

def stm_perform_transaction(initial_x=202):
    arg.x = initial_x
    ll_assert(rstm._debug_get_state() == -2, "bad debug_get_state (1)")
    rstm.descriptor_init()
    ll_assert(rstm._debug_get_state() == 0, "bad debug_get_state (2)")
    rstm.perform_transaction(setx, Arg, arg)
    ll_assert(rstm._debug_get_state() == 0, "bad debug_get_state (3)")
    rstm.descriptor_done()
    ll_assert(rstm._debug_get_state() == -2, "bad debug_get_state (4)")
    ll_assert(arg.x == 42, "bad arg.x")

def test_stm_multiple_threads():
    ok = []
    def f(i):
        stm_perform_transaction()
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

    def build_perform_transaction(self):
        from pypy.module.thread import ll_thread
        class Done: done = False
        done = Done()
        def g():
            stm_perform_transaction(done.initial_x)
            done.done = True
        def f(argv):
            done.initial_x = int(argv[1])
            assert rstm._debug_get_state() == -1    # main thread
            ll_thread.start_new_thread(g, ())
            for i in range(20):
                if done.done: break
                time.sleep(0.1)
            else:
                print "timeout!"
                raise Exception
            return 0
        t, cbuilder = self.compile(f)
        return cbuilder

    def test_perform_transaction(self):
        cbuilder = self.build_perform_transaction()
        #
        dataout, dataerr = cbuilder.cmdexec('202', err=True)
        assert dataout == ''
        assert '202' in dataerr.splitlines()
        #
        dataout, dataerr = cbuilder.cmdexec('303', err=True)
        assert 'hello' in dataout.splitlines()
        assert '303' in dataerr.splitlines()
