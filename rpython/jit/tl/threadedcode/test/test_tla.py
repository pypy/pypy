import py
import pytest
import os

from rpython.jit.tl.threadedcode import tla
from rpython.jit.tl.threadedcode.bytecode import Bytecode, assemble
from rpython.jit.tl.threadedcode.tla import \
    W_Object, W_IntObject, W_StringObject, Frame

def interp(mylist, w_arg):
    bytecode = Bytecode(assemble(mylist))
    return tla.run(bytecode, w_arg)

def interp_tier2(mylist, w_arg):
    bytecode = Bytecode(assemble(mylist))
    return tla.run(bytecode, w_arg, tier=2)

def read_code(name):
    path = "%s/../lang/%s" % (os.path.dirname(__file__), name)
    mydict = {}
    execfile(path, mydict)
    return mydict['code']

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
        code = read_code('../lang/loop.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [100])
        assert res == 0

    def test_jit_sum(self):
        code = read_code('../lang/sum.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [10])
        assert res == 55

    def test_jit_fib(self):
        code = read_code('../lang/fib.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [7])
        assert res == 8

    def test_jit_tak(self):
        code = read_code('../lang/tak.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [1])
        assert res == 4

    def test_jit_tarai(self):
        code = read_code('../lang/tarai.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [1])

    def test_jit_ack(self):
        code = read_code('../lang/ack.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue

        res = self.meta_interp(interp_w, [1])

    def test_jit_gcd(self):
        code = read_code('../lang/gcd.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue
        res = self.meta_interp(interp_w, [1])


    def test_jit_ary(self):
        code = read_code('../lang/ary.tla.py')
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue
        res = self.meta_interp(interp_w, [6])
