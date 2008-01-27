import py
from pypy.jit.tl.opcode import compile
from pypy.jit.tl.test import test_tl


class TestTLC(test_tl.TestTL):
    from pypy.jit.tl.tlc import interp
    interp = staticmethod(interp)

    def test_basic_cons_cell(self):
        bytecode = compile("""
            NIL
            PUSHARG
            CONS
            PUSH 1
            CONS
            CDR
            CAR
        """)

        res = self.interp(bytecode, 0, 42)
        assert res == 42

    def test_nth(self):
        bytecode = compile("""
            NIL
            PUSH 4
            CONS
            PUSH 2
            CONS
            PUSH 1
            CONS
            PUSHARG
            DIV
        """)

        res = self.interp(bytecode, 0, 0)
        assert res == 1
        res = self.interp(bytecode, 0, 1)
        assert res == 2
        res = self.interp(bytecode, 0, 2)
        assert res == 4

        py.test.raises(IndexError, self.interp, bytecode, 0, 3)
            
    def test_concat(self):
        bytecode = compile("""
            NIL
            PUSH 4
            CONS
            PUSH 2
            CONS
            NIL
            PUSH 5
            CONS
            PUSH 3
            CONS
            PUSH 1
            CONS
            ADD
            PUSHARG
            DIV
        """)

        for i, n in enumerate([2, 4, 1, 3, 5]):
            res = self.interp(bytecode, 0, i)
            assert res == n

    def test_concat_errors(self):
        bytecode = compile("""
            NIL
            PUSH 4
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)

        bytecode = compile("""
            PUSH 4
            NIL
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)


        bytecode = compile("""
            NIL
            PUSH 1
            CONS
            PUSH 4
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)

        bytecode = compile("""
            PUSH 4
            NIL
            PUSH 1
            CONS
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)


        bytecode = compile("""
            PUSH 2
            PUSH 1
            CONS
            NIL
            ADD
        """)
        py.test.raises(TypeError, self.interp, bytecode, 0, 0)

