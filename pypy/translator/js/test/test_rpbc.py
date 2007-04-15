
import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_rpbc import BaseTestRPBC

# ====> ../../../rpython/test/test_rpbc.py

class TestJsPBC(JsTest, BaseTestRPBC):
    def test_single_pbc_getattr(self):
        class C:
            def __init__(self, v1, v2):
                self.v1 = v1
                self.v2 = v2
            def _freeze_(self):
                return True
        c1 = C(11, lambda: "hello")
        c2 = C(22, lambda: 623)
        def f1(l, c):
            l.append(c.v1)
        def f2(c):
            return c.v2
        def f3(c):
            return c.v2
        def g():
            l = []
            f1(l, c1)
            f1(l, c2)
            return f2(c1)(), f3(c2)()

        res = self.interpret(g, [])
        assert res[0] == "hello"
        assert res[1] == 623

    def test_call_memoized_function_with_bools(self):
        py.test.skip("WIP")
        
