import py
from hypothesis import given
from rpython.jit.backend.llsupport.tl import code, interp
from rpython.jit.backend.llsupport.tl.stack import Stack
from rpython.jit.backend.llsupport.tl.test import code_strategies as st

class TestByteCode(object):
    def test_load_str(self):
        c = code.Context()
        code.LoadStr("hello world").encode(c)
        assert c.consts[0] == "hello world"
        assert c.get_byte(0) == code.LoadStr.BYTE_CODE
        assert c.get_short(1) == 0

    def test_str_add(self):
        c = code.Context()
        code.LoadStr("hello").encode(c)
        code.LoadStr("world").encode(c)
        code.AddStr().encode(c)
        assert len(c.consts) == 2
        assert c.get_byte(4) == code.AddStr.BYTE_CODE
        assert c.get_short(3) == 1

class TestInterp(object):
    @given(st.single_bytecode())
    def test_consume_stack(self, args):
        bytecode, consts, stack = args
        space = interp.Space()
        i = interp.dispatch_once(space, 0, bytecode, consts, stack)
        assert i == len(bytecode)
        clazz = code.get_byte_code_class(ord(bytecode[0]))
        assert stack.size() == len(clazz._return_on_stack_types)

    @given(st.bytecode_block())
    def test_execute_bytecode_block(self, args):
        bytecode, consts = args
        space = interp.Space()
        stack = Stack(16)
        pc = 0
        end = len(bytecode)
        while pc < end:
            pc = interp.dispatch_once(space, pc, bytecode, consts, stack)
        assert pc == len(bytecode)
