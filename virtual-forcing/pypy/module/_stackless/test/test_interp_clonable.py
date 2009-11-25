"""
testing cloning
"""
import py; py.test.skip("clonable coroutines not really maintained any more")

from pypy import conftest; conftest.translation_test_so_skip_if_appdirect()
from pypy.translator.c import gc
from pypy.rpython.memory.gctransform import stacklessframework
from pypy.rpython.memory.test import test_transformed_gc
from pypy.module._stackless.rclonable import InterpClonableCoroutine as ClonableCoroutine
from pypy.module._stackless.rclonable import AbstractThunk, fork

class TestClonableCoroutine(test_transformed_gc.GCTest):

    gcname = "marksweep"
    stacklessgc = True
    class gcpolicy(gc.StacklessFrameworkGcPolicy):
        class transformerclass(stacklessframework.StacklessFrameworkGCTransformer):
            GC_PARAMS = {'start_heap_size': 4096 }

    def test_clone(self):
        class T(AbstractThunk):
            def __init__(self, result):
                self.result = result
            def call(self):
                self.result.append(2)
                ClonableCoroutine.getmain().switch()
                self.result.append(4)
        def f():
            result = []
            coro = ClonableCoroutine()
            coro.bind(T(result))
            result.append(1)
            coro.switch()
            coro2 = coro.clone()
            result.append(3)
            coro2.switch()
            result.append(5)
            coro.switch()
            result.append(6)
            n = 0
            for i in result:
                n = n*10 + i
            return n

        run = self.runner(f)
        res = run([])
        assert res == 1234546

    def test_clone_local_state(self):
        class T(AbstractThunk):
            def __init__(self, result):
                self.result = result
            def call(self):
                localstate = []
                localstate.append(10)
                self.result.append(2)
                ClonableCoroutine.getmain().switch()
                localstate.append(20)
                if localstate == [10, 20]:
                    self.result.append(4)
                else:
                    self.result.append(0)
        def f():
            result = []
            coro = ClonableCoroutine()
            coro.bind(T(result))
            result.append(1)
            coro.switch()
            coro2 = coro.clone()
            result.append(3)
            coro2.switch()
            result.append(5)
            coro.switch()
            result.append(6)
            n = 0
            for i in result:
                n = n*10 + i
            return n

        run = self.runner(f)
        res = run([])
        assert res == 1234546

    def test_fork(self):
        class T(AbstractThunk):
            def __init__(self, result):
                self.result = result
            def call(self):
                localdata = [10]
                self.result.append(2)
                newcoro = fork()
                localdata.append(20)
                if newcoro is not None:
                    # in the parent
                    self.result.append(3)
                    newcoro.switch()
                    self.result.append(5)
                else:
                    # in the child
                    self.result.append(4)
                localdata.append(30)
                self.result.append(localdata != [10, 20, 30])
        def f():
            result = []
            coro = ClonableCoroutine()
            coro.bind(T(result))
            result.append(1)
            coro.switch()
            result.append(6)
            n = 0
            for i in result:
                n = n*10 + i
            return n

        run = self.runner(f)
        res = run([])
        assert res == 12340506
