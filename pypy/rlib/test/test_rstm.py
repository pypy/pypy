import os, thread, time
from pypy.rlib.debug import debug_print, ll_assert, fatalerror
from pypy.rlib import rstm
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.stm.test.support import CompiledSTMTests
from pypy.module.thread import ll_thread


class Arg(object):
    pass
arg_list = [Arg() for i in range(10)]

def setx(arg, retry_counter):
    debug_print(arg.x)
    assert rstm._debug_get_state() == 1
    if arg.x == 303:
        # this will trigger stm_become_inevitable()
        os.write(1, "hello\n")
        assert rstm._debug_get_state() == 2
    arg.x = 42

def stm_perform_transaction(done=None, i=0):
    ll_assert(rstm._debug_get_state() == -2, "bad debug_get_state (1)")
    rstm.descriptor_init()
    arg = arg_list[i]
    if done is None:
        arg.x = 202
    else:
        arg.x = done.initial_x
    ll_assert(rstm._debug_get_state() == 0, "bad debug_get_state (2)")
    rstm.perform_transaction(setx, Arg, arg)
    ll_assert(rstm._debug_get_state() == 0, "bad debug_get_state (3)")
    ll_assert(arg.x == 42, "bad arg.x")
    if done is not None:
        ll_thread.release_NOAUTO(done.finished_lock)
    rstm.descriptor_done()
    ll_assert(rstm._debug_get_state() == -2, "bad debug_get_state (4)")

def test_stm_multiple_threads():
    ok = []
    def f(i):
        stm_perform_transaction(i=i)
        ok.append(i)
    rstm.enter_transactional_mode()
    for i in range(10):
        thread.start_new_thread(f, (i,))
    timeout = 10
    while len(ok) < 10:
        time.sleep(0.1)
        timeout -= 0.1
        assert timeout >= 0.0, "timeout!"
    rstm.leave_transactional_mode()
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
        class Done: done = False
        done = Done()
        def g():
            stm_perform_transaction(done)
        def f(argv):
            done.initial_x = int(argv[1])
            assert rstm._debug_get_state() == -1    # main thread
            done.finished_lock = ll_thread.allocate_ll_lock()
            ll_thread.acquire_NOAUTO(done.finished_lock, True)
            #
            rstm.enter_transactional_mode()
            #
            llcallback = llhelper(ll_thread.CALLBACK, g)
            ident = ll_thread.c_thread_start_NOGIL(llcallback)
            ll_thread.acquire_NOAUTO(done.finished_lock, True)
            #
            rstm.leave_transactional_mode()
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
