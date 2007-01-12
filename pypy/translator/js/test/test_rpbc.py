
import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_rpbc import BaseTestRPBC

class Freezing:
    def _freeze_(self):
        return True
    def mymethod(self, y):
        return self.x + y

class TestJsPBC(JsTest, BaseTestRPBC):
    
    def test_call_memoized_function_with_bools(self):
        py.test.skip("WIP")

    def test_pbc_getattr_conversion_with_classes(self):
        class base: pass
        class fr1(base): pass
        class fr2(base): pass
        class fr3(base): pass
        fr1.value = 10
        fr2.value = 5
        fr3.value = 2.5
        def pick12(i):
            if i > 0:
                return fr1
            else:
                return fr2
        def pick23(i):
            if i > 5:
                return fr2
            else:
                return fr3
        def f(i):
            x = pick12(i)
            y = pick23(i)
            return x.value, y.value
        for i in [0, 5, 10]:
            res = self.interpret(f, [i])
            assert res == list(f(i))

    def test_pbc_getattr_conversion(self):
        fr1 = Freezing()
        fr2 = Freezing()
        fr3 = Freezing()
        fr1.value = 10
        fr2.value = 5
        fr3.value = 2.5
        def pick12(i):
            if i > 0:
                return fr1
            else:
                return fr2
        def pick23(i):
            if i > 5:
                return fr2
            else:
                return fr3
        def f(i):
            x = pick12(i)
            y = pick23(i)
            return x.value, y.value
        for i in [0, 5, 10]:
            res = self.interpret(f, [i])
            assert res == list(f(i))

    def test_conv_from_None(self):
        py.test.skip("WIP")



