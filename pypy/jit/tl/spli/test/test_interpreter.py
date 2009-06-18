from pypy.jit.tl.spli import interpreter, objects


class TestSPLIInterpreter:

    def eval(self, func):
        return interpreter.spli_run_from_cpython_code(func.func_code)

    def test_int_add(self):
        def f():
            return 4 + 6
        v = self.eval(f)
        assert isinstance(v, objects.Int)
        assert v.value == 10
        def f():
            a = 4
            return a + 6
        assert self.eval(f).value == 10

    def test_str(self):
        def f():
            return "Hi!"
        v = self.eval(f)
        assert isinstance(v, objects.Str)
        assert v.value == "Hi!"
        def f():
            a = "Hello, "
            return a + "SPLI world!"
        v = self.eval(f)
        assert isinstance(v, objects.Str)
        assert v.value == "Hello, SPLI world!"
