
from pypy.module.micronumpy.compile import *

class TestCompiler(object):
    def compile(self, code):
        return numpy_compile(code)
    
    def test_vars(self):
        code = """
        a = 2
        b = 3
        """
        interp = self.compile(code)
        assert isinstance(interp.code.statements[0], Assignment)
        assert interp.code.statements[0].name == 'a'
        assert interp.code.statements[0].expr.v == 2
        assert interp.code.statements[1].name == 'b'
        assert interp.code.statements[1].expr.v == 3

    def test_array_literal(self):
        code = "a = [1,2,3]"
        interp = self.compile(code)
        assert isinstance(interp.code.statements[0].expr, ArrayConstant)
        st = interp.code.statements[0]
        assert st.expr.items == [FloatConstant(1), FloatConstant(2),
                                 FloatConstant(3)]
    
    def test_array_literal2(self):
        code = "a = [[1],[2],[3]]"
        interp = self.compile(code)
        assert isinstance(interp.code.statements[0].expr, ArrayConstant)
        st = interp.code.statements[0]
        assert st.expr.items == [ArrayConstant([FloatConstant(1)]),
                                 ArrayConstant([FloatConstant(2)]),
                                 ArrayConstant([FloatConstant(3)])]

    def test_expr_1(self):
        code = "b = a + 1"
        interp = self.compile(code)
        assert (interp.code.statements[0].expr ==
                Operator(Variable("a"), "+", FloatConstant(1)))

    def test_expr_2(self):
        code = "b = a + b - 3"
        interp = self.compile(code)
        assert (interp.code.statements[0].expr ==
                Operator(Operator(Variable("a"), "+", Variable("b")), "-",
                         FloatConstant(3)))

    def test_expr_3(self):
        # an equivalent of range
        code = "a = |20|"
        interp = self.compile(code)
        assert interp.code.statements[0].expr == RangeConstant(20)

    def test_expr_only(self):
        code = "3 + a"
        interp = self.compile(code)
        assert interp.code.statements[0] == Execute(
            Operator(FloatConstant(3), "+", Variable("a")))

    def test_array_access(self):
        code = "a -> 3"
        interp = self.compile(code)
        assert interp.code.statements[0] == Execute(
            Operator(Variable("a"), "->", FloatConstant(3)))

    def test_function_call(self):
        code = "sum(a)"
        interp = self.compile(code)
        assert interp.code.statements[0] == Execute(
            FunctionCall("sum", [Variable("a")]))

class TestRunner(object):
    def run(self, code):
        interp = numpy_compile(code)
        space = FakeSpace()
        interp.run(space)
        return interp

    def test_one(self):
        code = """
        a = 3
        b = 4
        a + b
        """
        interp = self.run(code)
        assert sorted(interp.variables.keys()) == ['a', 'b']
        assert interp.results[0]

    def test_array_add(self):
        code = """
        a = [1,2,3,4]
        b = [4,5,6,5]
        a + b
        """
        interp = self.run(code)
        assert interp.results[0]._getnums(False) == ["5.0", "7.0", "9.0", "9.0"]

    def test_array_getitem(self):
        code = """
        a = [1,2,3,4]
        b = [4,5,6,5]
        a + b -> 3
        """
        interp = self.run(code)
        assert interp.results[0].value.val == 3 + 6
        
    def test_range_getitem(self):
        code = """
        r = |20| + 3
        r -> 3
        """
        interp = self.run(code)
        assert interp.results[0].value.val == 6

    def test_sum(self):
        code = """
        a = [1,2,3,4,5]
        r = sum(a)
        r
        """
        interp = self.run(code)
        assert interp.results[0].value.val == 15

    def test_array_write(self):
        code = """
        a = [1,2,3,4,5]
        a[3] = 15
        a -> 3
        """
        interp = self.run(code)
        assert interp.results[0].value.val == 15

    def test_min(self):
        interp = self.run("""
        a = |30|
        a[15] = -12
        b = a + a
        min(b)
        """)
        assert interp.results[0].value.val == -24

    def test_max(self):
        interp = self.run("""
        a = |30|
        a[13] = 128
        b = a + a
        max(b)
        """)
        assert interp.results[0].value.val == 256
