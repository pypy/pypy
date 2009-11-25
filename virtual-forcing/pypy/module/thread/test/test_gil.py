import time
from pypy.module.thread import gil
from pypy.module.thread.test import test_ll_thread
from pypy.rpython.lltypesystem import rffi
from pypy.module.thread import ll_thread as thread
from pypy.rlib.objectmodel import we_are_translated

class FakeEC(object):
    pass

class FakeActionFlag(object):
    def register_action(self, action):
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
    def getbuiltinmodule(self, name):
        raise NotImplementedError


class GILTests(test_ll_thread.AbstractGCTestClass):
    use_threads = True
    bigtest = False

    def test_one_thread(self):
        if self.bigtest:
            N = 1000000
        else:
            N = 100
        space = FakeSpace()
        class State:
            pass
        state = State()
        def runme():
            for i in range(N):
                state.data.append((thread.get_ident(), i))
                state.threadlocals.yield_thread()
        def bootstrap():
            try:
                runme()
            finally:
                thread.gc_thread_die()
        def f():
            state.data = []
            state.threadlocals = gil.GILThreadLocals()
            state.threadlocals.setup_threads(space)
            thread.gc_thread_prepare()
            subident = thread.start_new_thread(bootstrap, ())
            mainident = thread.get_ident()
            runme()
            still_waiting = 3000
            while len(state.data) < 2*N:
                if not still_waiting:
                    raise ValueError("time out")
                still_waiting -= 1
                if not we_are_translated(): gil.before_external_call()
                time.sleep(0.01)
                if not we_are_translated(): gil.after_external_call()
            i1 = i2 = 0
            for tid, i in state.data:
                if tid == mainident:
                    assert i == i1; i1 += 1
                elif tid == subident:
                    assert i == i2; i2 += 1
                else:
                    assert 0
            assert i1 == N
            assert i2 == N
            return len(state.data)

        fn = self.getcompiled(f, [])
        res = fn()
        assert res == 2*N


class TestRunDirectly(GILTests):
    def getcompiled(self, f, argtypes):
        return f

class TestUsingFramework(GILTests):
    gcpolicy = 'generation'
    bigtest = True
