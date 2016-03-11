import py
from hypothesis import given, settings, Verbosity
from hypothesis.strategies import lists, data
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

class TestCodeStrategies(object):
    DEFAULT_ACTION_CLASSES = (code.CreateList, code.PutInt,
         code.LoadStr)

    @given(data())
    def test_bytecode_class_generation(self, data):
        space = interp.Space()
        stack = Stack(0)
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz in self.DEFAULT_ACTION_CLASSES)

    @given(data())
    def test_bytecode_class_generation_int(self, data):
        space = interp.Space()
        stack = Stack(0)
        stack.append(space.wrap(0))
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz in self.DEFAULT_ACTION_CLASSES)
        stack.append(space.wrap(0))
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz in self.DEFAULT_ACTION_CLASSES + \
                            (code.CompareInt,))

    @given(data())
    def test_bytecode_class_generation_str(self, data):
        space = interp.Space()
        stack = Stack(0)
        stack.append(space.wrap("hello"))
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz in self.DEFAULT_ACTION_CLASSES)
        stack.append(space.wrap("world"))
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz in self.DEFAULT_ACTION_CLASSES + \
                            (code.AddStr,))

    @given(data())
    def test_bytecode_class_generation_list(self, data):
        space = interp.Space()
        stack = Stack(0)
        stack.append(space.wrap([]))
        stack.append(space.wrap(0))
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz not in (code.InsertList, code.DelList))
        stack.append(space.wrap([space.wrap(1)]))
        stack.append(space.wrap(0))
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz in self.DEFAULT_ACTION_CLASSES + \
                            (code.DelList, code.AppendList))
        stack.append(space.wrap("haskell"))
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert(clazz in self.DEFAULT_ACTION_CLASSES + \
                            (code.InsertList, code.AppendList))

    @given(data())
    def test_empty_stack_no_list_op(self, data):
        space = interp.Space()
        stack = Stack(0)
        for i in range(10):
            clazz = data.draw(st.bytecode_class(stack))
            assert not (clazz in (code.DelList, code.InsertList,
                                    code.AppendList, code.AddList,
                                    code.AddStr))

class TestInterp(object):

    @given(st.basic_block(st.bytecode(), min_size=1))
    def test_execute_bytecode_block(self, bc_obj_list):
        bytecode, consts = code.Context().transform(bc_obj_list)
        space = interp.Space()
        pc = 0
        end = len(bytecode)
        stack = Stack(0)
        while pc < end:
            pc = interp.dispatch_once(space, pc, bytecode, consts, stack)
        assert pc == len(bytecode)
