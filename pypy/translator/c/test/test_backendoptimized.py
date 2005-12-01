import autopath
from pypy.translator.c.test.test_typed import TestTypedTestCase as _TestTypedTestCase
from pypy.translator.backendopt.all import backend_optimizations


class TestTypedOptimizedTestCase(_TestTypedTestCase):

    def process(self, t):
        _TestTypedTestCase.process(self, t)
        backend_optimizations(t)

    def test_remove_same_as(self):
        def f(n=bool):
            if bool(bool(bool(n))):
                return 123
            else:
                return 456
        fn = self.getcompiled(f)
        assert f(True) == 123
        assert f(False) == 456
