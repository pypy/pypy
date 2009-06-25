import py
from pypy.jit.tl.spli import execution, objects

class TestSPLIInterpreter:

    def eval(self, func, args=[]):
        return execution.run_from_cpython_code(func.func_code, args)

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

    def test_comparison(self):
        def f(i):
            return i < 10

        v = self.eval(f, [0])
        assert isinstance(v, objects.Bool)
        assert v.value == True

    def test_while_loop(self):
        def f():
            i = 0
            while i < 100:
                i = i + 1
            return i

        v = self.eval(f)
        assert v.value == 100

    def test_invalid_adds(self):
        def f():
            "3" + 3
        py.test.raises(objects.W_TypeError, self.eval, f)
        def f():
            3 + "3"
        py.test.raises(objects.W_TypeError, self.eval, f)

    def test_call(self):
        code = compile("""
def g():
    return 4
def f():
    return g() + 3
res = f()""", "<string>", "exec")
        globs = {}
        mod_res = execution.run_from_cpython_code(code, [], globs, globs)
        assert mod_res is objects.spli_None
        assert len(globs) == 3
        assert globs["res"].as_int() == 7
