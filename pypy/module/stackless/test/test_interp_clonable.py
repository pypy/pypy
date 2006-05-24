"""
testing cloning
"""

from pypy.translator.c import gc
from pypy.rpython.memory import gctransform
from pypy.rpython.memory.test import test_transformed_gc
from pypy.module.stackless.interp_coroutine import costate
from pypy.module.stackless.interp_clonable import ClonableCoroutine
from pypy.module.stackless.interp_clonable import AbstractThunk, fork


class TestClonableCoroutine(test_transformed_gc.GCTest):

    class gcpolicy(gc.StacklessFrameworkGcPolicy):
        class transformerclass(gctransform.StacklessFrameworkGCTransformer):
            GC_PARAMS = {'start_heap_size': 4096 }

    def test_clone(self):
        class T(AbstractThunk):
            def __init__(self, result):
                self.result = result
            def call(self):
                self.result.append(2)
                costate.main.switch()
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

    def test_fork(self):
        import py; py.test.skip("in-progress")
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
            result.append(5)
            coro.switch()   # resume after newcoro.switch()
            result.append(6)
            n = 0
            for i in result:
                n = n*10 + i
            return n

        run = self.runner(f)
        res = run([])
        assert res == 12340506
