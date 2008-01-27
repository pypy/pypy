from pypy.rlib.jit import we_are_jitted, _is_early_constant, hint
from pypy.rpython.test.test_llinterp import interpret
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests

class TestFrontend(TimeshiftingTests):

    def test_we_are_jitted(self):
        def f():
            if we_are_jitted():
                return 42
            return 0

        assert f() == 0
        res = interpret(f, [])
        assert res == 0

        res = self.timeshift(f, [])
        assert res == 42

    def test_is_early_constant(self):
        def f(x):
            if _is_early_constant(x):
                return 42
            return 0

        res = self.timeshift(f, [5])
        assert res == 0
        res = self.timeshift(f, [5], [0])
        assert res == 42

    def test_is_early_constant_for_green(self):
        def g(x):
            if _is_early_constant(x):
                return 42
            hint(x, concrete=True)
            return 0
        
        res = self.timeshift(g, [5])
        assert res == 42        
