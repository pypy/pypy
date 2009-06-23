from pypy.jit.tl.spli import interpreter, objects

class TestSPLIInterpreter:

    def eval(self, func, args=[]):
        return interpreter.spli_run_from_cpython_code(func.func_code, args)

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
        
