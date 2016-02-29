import py
from hypothesis import given
from rpython.jit.backend.llsupport.tl import code, stack, interp
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
        clazz, bytecode, consts, stack = args
        space = interp.Space()
        i = interp.dispatch_once(space, 0, bytecode, consts, stack)
        assert i == len(bytecode)
        assert stack.size() == len(clazz._return_on_stack_types)
