import py
from hypothesis import given
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


class TestInterp(object):
    @given(st.bytecode())
    def test_consume_stack(self, args):
        bc_obj, stack = args
        bytecode, consts = code.Context().transform([bc_obj])
        space = interp.Space()
        i = interp.dispatch_once(space, 0, bytecode, consts, stack)
        assert i == len(bytecode)
        clazz = st.get_byte_code_class(ord(bytecode[0]))
        assert stack.size() >= len(clazz._return_on_stack_types)
        for i,type in enumerate(clazz._return_on_stack_types):
            j = len(clazz._return_on_stack_types) - i - 1
            assert stack.peek(j).is_of_type(type)

    @given(lists(st.bytecode(max_stack_size=0), min_size=1))
    def test_execute_bytecode_block(self, codes):
        bc_obj_list = [bc for bc,stack in codes]
        _, stack = codes[0]
        bytecode, consts = code.Context().transform(bc_obj_list)
        space = interp.Space()
        stack = Stack(16)
        pc = 0
        end = len(bytecode)
        while pc < end:
            pc = interp.dispatch_once(space, pc, bytecode, consts, stack)
        assert pc == len(bytecode)
