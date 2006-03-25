from pypy.translator.squeak.test.runtest import compile_function

class TestTuple:

    def test_twotuple(self):
        def f(i):
            # Use two different two-tuples to make sure gensqueak can cope
            # with the two different classes.
            b = (True, i)
            if b[0]:
                i = b[1] + 1
            if i > 0:
                return (i, 1)
            else:
                return (i, -1)
        def g(i):
            return f(i)[1]
        fn = compile_function(g, [int])
        res = fn(2)
        assert res == "1"
        res = fn(-2)
        assert res == "-1"

    def DONT_test_tupleiter(self):
        def f(i):
            t = (i,)
            for x in t:
                i += x
            return t
        fn = compile_function(f, [int])
        res = fn(2)
        assert res == "4"
