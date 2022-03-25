import py
import pytest

from rpython.jit.tl.threadedcode import tla
from rpython.jit.tl.threadedcode.tla import \
    W_Object, W_IntObject, W_StringObject, Frame

def assemble(mylist):
    return ''.join([chr(x) for x in mylist])

def interp(mylist, w_arg):
    bytecode = assemble(mylist)
    return tla.run(bytecode, w_arg)

def assert_stack(stack1, stack2):
    for x, y in zip(stack1, stack2):
        if x is None and y is None:
            continue
        assert x.eq(y)

class TestFrame:

    def test_add(self):
        code = [
            tla.CONST_INT, 123,
            tla.ADD,
            tla.EXIT
        ]
        res = interp(code, W_IntObject(123))
        assert res.intvalue == 123 + 123

    def test_sub(self):
        code = [
            tla.CONST_INT, 123,
            tla.SUB,
            tla.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 - 123

    def test_mul(self):
        code = [
            tla.CONST_INT, 123,
            tla.MUL,
            tla.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 * 123

    def test_div(self):
        code = [
            tla.CONST_INT, 123,
            tla.DIV,
            tla.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 / 123

    def test_mod(self):
        code = [
            tla.CONST_INT, 2,
            tla.MOD,
            tla.EXIT
        ]
        res = interp(code, W_IntObject(10))
        assert res.intvalue == 0
        res = interp(code, W_IntObject(13))
        assert res.intvalue == 1

    def test_jump(self):
        code = [
            tla.JUMP, 3,
            tla.ADD,
            tla.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234

    def test_call(self):
        code = [
            tla.CALL, 3,
            tla.EXIT,
            tla.CONST_INT, 12,
            tla.ADD,
            tla.RET, 1
        ]
        res = interp(code, W_IntObject(34))
        assert res.intvalue == 34 + 12

    def test_frame_reset(self):
        stack = [
            W_IntObject(10), # ?
            W_IntObject(0),  # old acc
            W_IntObject(10), # old n
            W_IntObject(-1), # dummy ret_addr
            W_IntObject(10), # local acc
            W_IntObject(9)   # local n
        ]
        code = [ tla.FRAME_RESET, 2, 2, 2, ]
        frame = Frame(assemble(code))
        frame.stack = stack
        frame.stackpos = len(stack)
        frame.interp()

        expected = [
            W_IntObject(10),
            W_IntObject(10),
            W_IntObject(9),
            W_IntObject(-1), # dummy ret_addr
            None,
            None
        ]

        assert_stack(frame.stack, expected)

    def test_simple_loop(self):
        code = [
            tla.DUP,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 11,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.JUMP, 0,
            tla.EXIT,
        ]
        res = interp(code, W_IntObject(100))
        assert res.intvalue == 0

    def test_double_loop(self):
        code = [
            tla.DUP,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 12,
            tla.JUMP, 1,
            tla.POP,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.DUP,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 25,
            tla.JUMP, 1,
            tla.EXIT
        ]
        res = interp(code, W_IntObject(3))
        assert res.intvalue == 0

from rpython.jit.metainterp.test.support import LLJitMixin

class TestLLType(LLJitMixin):

    def test_jit_loop(self):
        code = [
            tla.DUP,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 11,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.JUMP, 0,
            tla.CONST_INT, 10,
            tla.SUB,
            tla.EXIT,
        ]
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue
        res = self.meta_interp(interp_w, [42])
        assert res == -10

    def test_jit_loopabit(self):
        code = [
            tla.DUP,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 12,
            tla.JUMP, 1,
            tla.POP,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.DUP,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 25,
            tla.JUMP, 1,
            tla.EXIT
        ]
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue
        res = self.meta_interp(interp_w, [42])
        assert res == 0

    def test_jit_sum(self):
        code = [
            tla.NOP,
            tla.DUP,
            tla.DUP,
            tla.CALL_ASSEMBLER, 10, 1,
            tla.PRINT,
            tla.POP1,
            tla.POP1,
            tla.EXIT,
            tla.DUPN, 1,
            tla.CONST_INT, 0,
            tla.GT,
            tla.JUMP_IF, 21,
            tla.DUPN, 1,
            tla.JUMP, 37,
            tla.DUPN, 1,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.CALL_ASSEMBLER, 10, 1,
            tla.DUPN, 3,
            tla.DUPN, 1,
            tla.ADD,
            tla.POP1,
            tla.POP1,
            tla.RET, 1,
        ]
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [5])
        assert res == 15

    def test_jit_fib(self):
        code = [
            tla.DUP,
            tla.NOP,
            tla.DUP,
            tla.CALL, 10, 1,
            tla.PRINT,
            tla.POP1,
            tla.POP1,
            tla.EXIT,
            tla.DUPN, 1,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 46,
            tla.DUPN, 1,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.CALL, 10, 1,
            tla.DUPN, 3,
            tla.CONST_INT, 2,
            tla.SUB,
            tla.DUP,
            tla.CALL, 10, 1,
            tla.DUPN, 2,
            tla.DUPN, 1,
            tla.ADD,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.JUMP, 48,
            tla.CONST_INT, 1,
            tla.RET, 1,
        ]

        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [6])
        assert res == 8

    def test_jit_tak(self):
        code = [
            tla.CONST_INT, 12,
            tla.CONST_INT, 5,
            tla.CONST_INT, 3,
            tla.DUPN, 2,
            tla.DUPN, 2,
            tla.DUPN, 2,
            tla.CALL, 21, 3,
            tla.PRINT,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.EXIT,
            tla.DUPN, 3,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUPN, 3,
            tla.DUPN, 1,
            tla.LT,
            tla.JUMP_IF, 37,
            tla.DUPN, 2,
            tla.JUMP, 94,
            tla.DUPN, 4,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.DUPN, 5,
            tla.DUPN, 5,
            tla.CALL, 21, 3,
            tla.DUPN, 5,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.DUPN, 6,
            tla.DUPN, 9,
            tla.CALL, 21, 3,
            tla.DUPN, 6,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.DUPN, 10,
            tla.DUPN, 10,
            tla.CALL, 21, 3,
            tla.DUPN, 4,
            tla.DUPN, 3,
            tla.DUPN, 2,
            tla.FRAME_RESET, 3, 7, 3,
            tla.JUMP, 21,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.RET, 3,
        ]
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [6])


    def test_jit_ack(self):
        code = [
            tla.CONST_INT, 2,
            tla.CONST_INT, 2,
            tla.DUPN, 1,
            tla.DUPN, 1,
            tla.CALL, 16, 2,
            tla.PRINT,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.EXIT,
            tla.DUPN, 2,
            tla.CONST_INT, 1,
            tla.GT,
            tla.JUMP_IF, 30,
            tla.DUPN, 1,
            tla.CONST_INT, 1,
            tla.ADD,
            tla.JUMP, 80,
            tla.DUPN, 1,
            tla.CONST_INT, 1,
            tla.GT,
            tla.JUMP_IF, 54,
            tla.DUPN, 2,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.CONST_INT, 1,
            tla.DUPN, 1,
            tla.DUPN, 1,
            tla.JUMP, 16,
            tla.POP1,
            tla.POP1,
            tla.JUMP, 80,
            tla.DUPN, 2,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUPN, 2,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUPN, 4,
            tla.DUPN, 1,
            tla.CALL, 16, 2,
            tla.DUPN, 2,
            tla.DUPN, 1,
            tla.JUMP, 16,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.RET, 2,
        ]
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [6])

    def test_jit_gcd(self):
        code = [
            tla.CONST_INT, 21,
            tla.CONST_INT, 33,
            tla.DUPN, 1,
            tla.DUPN, 1,
            tla.CALL, 16, 2,
            tla.PRINT,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.EXIT,
            tla.DUPN, 2,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.CONST_INT, 0,
            tla.GT,
            tla.JUMP_IF, 31,
            tla.DUPN, 2,
            tla.JUMP, 70,
            tla.DUPN, 3,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUPN, 3,
            tla.DUPN, 1,
            tla.LT,
            tla.JUMP_IF, 57,
            tla.DUPN, 3,
            tla.DUPN, 5,
            tla.SUB,
            tla.DUPN, 5,
            tla.DUPN, 1,
            tla.JUMP, 16,
            tla.POP1,
            tla.JUMP, 69,
            tla.DUPN, 4,
            tla.DUPN, 4,
            tla.SUB,
            tla.DUPN, 4,
            tla.DUPN, 1,
            tla.JUMP, 16,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.RET, 2,
        ]

        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [6])

    def test_jit_sumfib(self):
        code = [
            tla.CONST_INT, 10,
            tla.CONST_INT, 0,
            tla.DUPN, 1,
            tla.DUPN, 1,
            tla.CALL_ASSEMBLER, 56, 2,
            tla.PRINT,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.EXIT,
            tla.DUPN, 1,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 52,
            tla.DUPN, 1,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.CALL_ASSEMBLER, 16, 1,
            tla.DUPN, 3,
            tla.CONST_INT, 2,
            tla.SUB,
            tla.DUP,
            tla.CALL_ASSEMBLER, 16, 1,
            tla.DUPN, 2,
            tla.DUPN, 1,
            tla.ADD,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.JUMP, 54,
            tla.CONST_INT, 1,
            tla.RET, 1,
            tla.DUPN, 2,
            tla.CONST_INT, 1,
            tla.LT,
            tla.JUMP_IF, 95,
            tla.CONST_INT, 10,
            tla.DUP,
            tla.CALL_ASSEMBLER, 16, 1,
            tla.DUPN, 4,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUPN, 4,
            tla.DUPN, 2,
            tla.ADD,
            tla.DUPN, 1,
            tla.DUPN, 1,
            tla.FRAME_RESET, 2, 4, 2,
            tla.JUMP, 56,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.JUMP, 97,
            tla.DUPN, 1,
            tla.RET, 2,
        ]

        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [6])

    def test_jit_ary(self):

        code = [
            tla.CONST_INT, 100,
            tla.CONST_INT, 1,
            tla.DUP,
            tla.DUPN, 2,
            tla.BUILD_LIST,
            tla.CONST_INT, 2,
            tla.DUP,
            tla.DUPN, 4,
            tla.BUILD_LIST,
            tla.CONST_INT, 3,
            tla.DUP,
            tla.DUPN, 6,
            tla.BUILD_LIST,
            tla.CONST_INT, 0,
            tla.DUP,
            tla.DUPN, 8,
            tla.DUPN, 7,
            tla.DUPN, 6,
            tla.DUPN, 5,
            tla.CALL, 50, 5,
            tla.DUP,
            tla.CONST_INT, 0,
            tla.LOAD,
            tla.PRINT,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.EXIT,
            tla.DUPN, 4,
            tla.CONST_INT, 1,
            tla.SUB,
            tla.DUP,
            tla.DUPN, 7,
            tla.LT,
            tla.JUMP_IF, 109,
            tla.DUPN, 4,
            tla.DUPN, 7,
            tla.LOAD,
            tla.DUPN, 4,
            tla.DUPN, 8,
            tla.LOAD,
            tla.DUPN, 1,
            tla.DUPN, 1,
            tla.ADD,
            tla.DUP,
            tla.DUPN, 6,
            tla.DUPN, 11,
            tla.STORE,
            tla.DUPN, 10,
            tla.CONST_INT, 1,
            tla.ADD,
            tla.DUP,
            tla.DUPN, 11,
            tla.DUPN, 11,
            tla.DUPN, 11,
            tla.DUPN, 11,
            tla.FRAME_RESET, 5, 6, 5,
            tla.JUMP, 50,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.POP1,
            tla.JUMP, 111,
            tla.DUPN, 2,
            tla.POP1,
            tla.RET, 5,
        ]

        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [6])
