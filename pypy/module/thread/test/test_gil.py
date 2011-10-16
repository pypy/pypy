import time
from pypy.module.thread import gil
from pypy.module.thread.test import test_ll_thread
from pypy.module.thread import ll_thread as thread
from pypy.rlib.objectmodel import we_are_translated

class FakeEC(object):
    pass

class FakeActionFlag(object):
    def register_periodic_action(self, action, use_bytecode_counter):
        pass
    def get(self):
        return 0
    def set(self, x):
        pass

class FakeSpace(object):
    def __init__(self):
        self.actionflag = FakeActionFlag()
    def _freeze_(self):
        return True
    def getexecutioncontext(self):
        return FakeEC()
    def fromcache(self, key):
        raise NotImplementedError


class GILTests(test_ll_thread.AbstractGCTestClass):
    use_threads = True
    bigtest = False

    def test_one_thread(self, skew=+1):
        from pypy.rlib.debug import debug_print
        if self.bigtest:
            N = 100000
            skew *= 25000
        else:
            N = 100
            skew *= 25
        space = FakeSpace()
        class State:
            pass
        state = State()
        def runme(main=False):
            j = 0
            for i in range(N + [-skew, skew][main]):
                state.datalen1 += 1   # try to crash if the GIL is not
                state.datalen2 += 1   # correctly acquired
                state.data.append((thread.get_ident(), i))
                state.datalen3 += 1
                state.datalen4 += 1
                assert state.datalen1 == len(state.data)
                assert state.datalen2 == len(state.data)
                assert state.datalen3 == len(state.data)
                assert state.datalen4 == len(state.data)
                debug_print(main, i, state.datalen4)
                state.threadlocals.yield_thread()
                assert i == j
                j += 1
        def bootstrap():
            try:
                runme()
            finally:
                thread.gc_thread_die()
        def f():
            state.data = []
            state.datalen1 = 0
            state.datalen2 = 0
            state.datalen3 = 0
            state.datalen4 = 0
            state.threadlocals = gil.GILThreadLocals()
            state.threadlocals.setup_threads(space)
            thread.gc_thread_prepare()
            subident = thread.start_new_thread(bootstrap, ())
            mainident = thread.get_ident()
            runme(True)
            still_waiting = 3000
            while len(state.data) < 2*N:
                debug_print(len(state.data))
                if not still_waiting:
                    raise ValueError("time out")
                still_waiting -= 1
                if not we_are_translated(): gil.before_external_call()
                time.sleep(0.01)
                if not we_are_translated(): gil.after_external_call()
            debug_print("leaving!")
            i1 = i2 = 0
            for tid, i in state.data:
                if tid == mainident:
                    assert i == i1; i1 += 1
                elif tid == subident:
                    assert i == i2; i2 += 1
                else:
                    assert 0
            assert i1 == N + skew
            assert i2 == N - skew
            return len(state.data)

        fn = self.getcompiled(f, [])
        res = fn()
        assert res == 2*N

    def test_one_thread_rev(self):
        self.test_one_thread(skew=-1)


class TestRunDirectly(GILTests):
    def getcompiled(self, f, argtypes):
        return f

class TestUsingFramework(GILTests):
    gcpolicy = 'generation'
    bigtest = True
