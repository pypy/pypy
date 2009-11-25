import py
from pypy.lang.smalltalk import model, interpreter, primitives, shadow
from pypy.lang.smalltalk import objspace

mockclass = objspace.bootstrap_class

space = objspace.ObjSpace()

# expose the bytecode's values as global constants.
# Bytecodes that have a whole range are exposed as global functions:
# call them with an argument 'n' to get the bytecode number 'base + n'.
# XXX hackish
def setup():
    def make_getter(entry):
        def get_opcode_chr(n):
            opcode = entry[0] + n
            assert entry[0] <= opcode <= entry[1]
            return chr(opcode)
        return get_opcode_chr
    for entry in interpreter.BYTECODE_RANGES:
        name = entry[-1].__name__
        if len(entry) == 2:     # no range
            globals()[name] = chr(entry[0])
        else:
            globals()[name] = make_getter(entry)
setup()

def run_with_faked_methods(methods, func):

    # Install faked compiled methods that just invoke the primitive:
    for (w_class, primnum, argsize, methname) in methods:
        s_class = w_class.as_class_get_shadow(space)
        prim_meth = model.W_CompiledMethod(0)
        prim_meth.primitive = primnum
        prim_meth.w_compiledin = w_class
        prim_meth.argsize = argsize
        s_class.installmethod(methname, prim_meth)
        
        assert space.w_nil._shadow is None
    try:
        func()
    finally:
        # Uninstall those methods:
        assert space.w_nil._shadow is None
        for (w_class, _, _, methname) in methods:
            s_class = w_class.as_class_get_shadow(space)
            del s_class.s_methoddict().methoddict[methname]

def fakesymbol(s, _cache={}):
    try:
        return _cache[s]
    except KeyError:
        result = _cache[s] = space.wrap_string(s)
        return result

def fakeliterals(space, *literals):
    def fakeliteral(lit):
        if isinstance(lit, str):
            return fakesymbol(lit)
        elif isinstance(lit, int):
            return space.wrap_int(lit)
        elif isinstance(lit, list):
            lstlen = len(lit)
            res = space.w_Array.as_class_get_shadow(space).new(lstlen)
            for i in range(lstlen):
                res.atput0(space, i, fakeliteral(lit[i]))
            return res
        return lit
    return [fakeliteral(lit) for lit in literals]

def new_interpreter(bytes, receiver=space.w_nil):
    assert isinstance(bytes, str)
    w_method = model.W_CompiledMethod(len(bytes))
    w_method.islarge = 1
    w_method.bytes = bytes
    w_method.argsize=2
    w_method.tempsize=8
    w_frame = w_method.create_frame(space, receiver, ["foo", "bar"])
    interp = interpreter.Interpreter(space)
    interp.store_w_active_context(w_frame)
    return interp

def test_create_frame():
    w_method = model.W_CompiledMethod(len("hello"))
    w_method.bytes="hello"
    w_method.islarge = 1
    w_method.argsize=2
    w_method.tempsize=8
    w_frame = w_method.create_frame(space, "receiver", ["foo", "bar"])
    s_frame = w_frame.as_context_get_shadow(space)
    assert s_frame.w_receiver() == "receiver"
    assert s_frame.gettemp(0) == "foo"
    assert s_frame.gettemp(1) == "bar"
    assert s_frame.gettemp(2) is space.w_nil
    s_frame.settemp(2, "spam")
    assert s_frame.gettemp(2) == "spam"
    assert s_frame.getNextBytecode() == ord("h")
    assert s_frame.getNextBytecode() == ord("e")
    assert s_frame.getNextBytecode() == ord("l")

def test_push_pop():
    interp = new_interpreter("")
    frame = interp.s_active_context()
    frame.push(12)
    frame.push(34)
    frame.push(56)
    assert frame.peek(2) == 12
    assert frame.pop() == 56
    assert frame.top() == 34
    frame.pop_n(0)
    assert frame.top() == 34
    frame.push(56)
    frame.pop_n(2)
    assert frame.top() == 12

def test_unknownBytecode():
    interp = new_interpreter(unknownBytecode)
    py.test.raises(interpreter.MissingBytecode, interp.interpret)

# push bytecodes
def test_pushReceiverBytecode():
    interp = new_interpreter(pushReceiverBytecode)
    interp.step()
    assert interp.s_active_context().top().is_same_object(
            interp.w_active_context().as_methodcontext_get_shadow(space).w_receiver())

def test_pushReceiverVariableBytecode(bytecode = (pushReceiverVariableBytecode(0) +
                                                  pushReceiverVariableBytecode(1) +
                                                  pushReceiverVariableBytecode(2))):
    w_demo = mockclass(space, 3).as_class_get_shadow(space).new()
    w_demo.store(space, 0, "egg")
    w_demo.store(space, 1, "bar")
    w_demo.store(space, 2, "baz")
    interp = new_interpreter(bytecode, receiver = w_demo)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().stack() == ["egg", "bar", "baz"]

def test_pushTemporaryVariableBytecode(bytecode=(pushTemporaryVariableBytecode(0) +
                                                 pushTemporaryVariableBytecode(1) +
                                                 pushTemporaryVariableBytecode(2))):
    interp = new_interpreter(bytecode)
    interp.w_active_context().as_methodcontext_get_shadow(space).settemp(2, "temp")
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().stack() == ["foo", "bar", "temp"]

def test_pushLiteralConstantBytecode(bytecode=pushLiteralConstantBytecode(0) +
                                              pushLiteralConstantBytecode(1) +
                                              pushLiteralConstantBytecode(2)):
    interp = new_interpreter(bytecode)
    interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = fakeliterals(space, "a", "b", "c")
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().stack() == [fakesymbol("a"),
                                             fakesymbol("b"),
                                             fakesymbol("c")]

def test_pushLiteralVariableBytecode(bytecode=pushLiteralVariableBytecode(0)):
    w_association = mockclass(space, 2).as_class_get_shadow(space).new()
    w_association.store(space, 0, "mykey")
    w_association.store(space, 1, "myvalue")
    interp = new_interpreter(bytecode)
    interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = fakeliterals(space, w_association)
    interp.step()
    assert interp.s_active_context().stack() == ["myvalue"]

def test_storeAndPopReceiverVariableBytecode(bytecode=storeAndPopReceiverVariableBytecode,
                                             popped=True):
    shadow = mockclass(space, 8).as_class_get_shadow(space)
    for index in range(8):
        w_object = shadow.new()
        interp = new_interpreter(pushConstantTrueBytecode + bytecode(index))
        interp.w_active_context().as_methodcontext_get_shadow(space).store_w_receiver(w_object)
        interp.step()
        interp.step()
        if popped:
            assert interp.s_active_context().stack() == []
        else:
            assert interp.s_active_context().stack() == [space.w_true]

        for test_index in range(8):
            if test_index == index:
                assert w_object.fetch(space, test_index).is_same_object(space.w_true)
            else:
                assert w_object.fetch(space, test_index) is space.w_nil

def test_storeAndPopTemporaryVariableBytecode(bytecode=storeAndPopTemporaryVariableBytecode):
    for index in range(8):
        interp = new_interpreter(pushConstantTrueBytecode + bytecode(index))
        #interp.w_active_context().as_methodcontext_get_shadow(space).temps = [None] * 8
        interp.step()
        interp.step()
        assert interp.s_active_context().stack() == []
        interp.w_active_context().as_methodcontext_get_shadow(space)
        for test_index in range(8):
            print interp.w_active_context()._vars
            if test_index == index:
                assert interp.s_active_context().gettemp(test_index) == space.w_true
            else:
                assert interp.s_active_context().gettemp(test_index) != space.w_true

def test_pushConstantTrueBytecode():
    interp = new_interpreter(pushConstantTrueBytecode)
    interp.step()
    assert interp.s_active_context().pop().is_same_object(space.w_true)
    assert interp.s_active_context().stack() == []

def test_pushConstantFalseBytecode():
    interp = new_interpreter(pushConstantFalseBytecode)
    interp.step()
    assert interp.s_active_context().pop().is_same_object(space.w_false)
    assert interp.s_active_context().stack() == []

def test_pushConstantNilBytecode():
    interp = new_interpreter(pushConstantNilBytecode)
    interp.step()
    assert interp.s_active_context().pop().is_same_object(space.w_nil)
    assert interp.s_active_context().stack() == []

def test_pushConstantMinusOneBytecode():
    interp = new_interpreter(pushConstantMinusOneBytecode)
    interp.step()
    assert interp.s_active_context().pop().is_same_object(space.w_minus_one)
    assert interp.s_active_context().stack() == []

def test_pushConstantZeroBytecode():
    interp = new_interpreter(pushConstantZeroBytecode)
    interp.step()
    assert interp.s_active_context().pop().is_same_object(space.w_zero)
    assert interp.s_active_context().stack() == []
    
def test_pushConstantOneBytecode():
    interp = new_interpreter(pushConstantOneBytecode)
    interp.step()
    assert interp.s_active_context().pop().is_same_object(space.w_one)
    assert interp.s_active_context().stack() == []

def test_pushConstantTwoBytecode():
    interp = new_interpreter(pushConstantTwoBytecode)
    interp.step()
    assert interp.s_active_context().pop().is_same_object(space.w_two)
    assert interp.s_active_context().stack() == []

def test_pushActiveContextBytecode():
    interp = new_interpreter(pushActiveContextBytecode)
    interp.step()
    assert interp.s_active_context().pop() == interp.w_active_context()
    assert interp.s_active_context().stack() == []
    
def test_duplicateTopBytecode():
    interp = new_interpreter(pushConstantZeroBytecode + duplicateTopBytecode)
    interp.step()
    interp.step()
    assert interp.s_active_context().stack() == [space.w_zero, space.w_zero]
    
def test_bytecodePrimBitAnd():
    interp = new_interpreter(pushConstantOneBytecode + pushConstantTwoBytecode + bytecodePrimBitAnd)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == 0
    assert interp.s_active_context().stack() == []
    
def test_bytecodePrimBitOr():
    interp = new_interpreter(pushConstantOneBytecode + pushConstantTwoBytecode + bytecodePrimBitOr)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == 3
    assert interp.s_active_context().stack() == []

def test_bytecodePrimBitShift():
    interp = new_interpreter(pushConstantOneBytecode + pushConstantTwoBytecode + bytecodePrimBitShift)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == 4
    assert interp.s_active_context().stack() == []
    
def test_bytecodePrimClass():
    interp = new_interpreter(pushConstantOneBytecode + bytecodePrimClass)
    interp.step()
    interp.step()
    assert interp.s_active_context().pop() == space.w_SmallInteger
    assert interp.s_active_context().stack() == []
    
def test_bytecodePrimSubtract():
    interp = new_interpreter(pushConstantOneBytecode + pushConstantTwoBytecode + bytecodePrimSubtract)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == -1
    assert interp.s_active_context().stack() == []

def test_bytecodePrimMultiply():
    interp = new_interpreter(pushConstantMinusOneBytecode + pushConstantTwoBytecode + bytecodePrimMultiply)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == -2
    assert interp.s_active_context().stack() == []
    
def test_bytecodePrimDivide():
    interp = new_interpreter(pushConstantTwoBytecode + pushConstantMinusOneBytecode + bytecodePrimDivide)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == -2    
    assert interp.s_active_context().stack() == []
    
def test_bytecodePrimDiv():
    interp = new_interpreter(pushConstantTwoBytecode + pushConstantMinusOneBytecode + bytecodePrimDiv)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == -2
    assert interp.s_active_context().stack() == []

def test_bytecodePrimMod():
    interp = new_interpreter(pushConstantTwoBytecode + pushConstantMinusOneBytecode + bytecodePrimMod)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop().value == 0
    assert interp.s_active_context().stack() == []

def test_bytecodePrimEquivalent():
    interp = new_interpreter(pushConstantTwoBytecode + pushConstantMinusOneBytecode + bytecodePrimEquivalent)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop() == space.w_false
    assert interp.s_active_context().stack() == []
    
    interp = new_interpreter(pushConstantOneBytecode + pushConstantOneBytecode + bytecodePrimEquivalent)
    interp.step()
    interp.step()
    interp.step()
    assert interp.s_active_context().pop() == space.w_true
    assert interp.s_active_context().stack() == []
    
def test_bytecodePrimNew():
    w_fakeclassclass = mockclass(space, 10, name='fakeclassclass')
    w_fakeclass = mockclass(space, 1, name='fakeclass', varsized=False,
                            w_metaclass=w_fakeclassclass)
    interp = new_interpreter(bytecodePrimNew)
    interp.s_active_context().push(w_fakeclass)
    run_with_faked_methods(
        [[w_fakeclassclass, primitives.NEW, 0, "new"]],
        interp.step)
    w_fakeinst = interp.s_active_context().pop()
    assert interp.s_active_context().stack() == []
    assert w_fakeinst.getclass(space).is_same_object(w_fakeclass)
    assert w_fakeinst.size() == 1
    
def test_bytecodePrimNewWithArg():
    w_fakeclassclass = mockclass(space, 10, name='fakeclassclass')
    w_fakeclass = mockclass(space, 1, name='fakeclass', varsized=True,
                            w_metaclass=w_fakeclassclass)
    interp = new_interpreter(bytecodePrimNewWithArg)
    interp.s_active_context().push(w_fakeclass)
    interp.s_active_context().push(space.w_two)
    run_with_faked_methods(
        [[w_fakeclassclass, primitives.NEW_WITH_ARG, 1, "new:"]],
        interp.step)
    w_fakeinst = interp.s_active_context().pop()
    assert interp.s_active_context().stack() == []
    assert w_fakeinst.getclass(space).is_same_object(w_fakeclass)
    assert w_fakeinst.size() == 3
 
def test_bytecodePrimSize():
    w_fakeclass = mockclass(space, 2, name='fakeclass', varsized=True)
    w_fakeinst = w_fakeclass.as_class_get_shadow(space).new(5)
    interp = new_interpreter(bytecodePrimSize)
    interp.s_active_context().push(w_fakeinst)
    run_with_faked_methods(
        [[w_fakeclass, primitives.SIZE, 0, "size"]],
        interp.step)
    assert interp.s_active_context().pop().value == 5
    assert interp.s_active_context().stack() == []

# w_class - the class from which the method is going to be called
# (and on which it is going to be installed)
# w_object - the actual object we will be sending the method to
# bytecodes - the bytecode to be executed
def sendBytecodesTest(w_class, w_object, bytecodes):
    for bytecode, result in [ (returnReceiver, w_object), 
          (returnTrue, space.w_true), 
          (returnFalse, space.w_false),
          (returnNil, space.w_nil),
          (returnTopFromMethod, space.w_one) ]:
        shadow = w_class.as_class_get_shadow(space)
        w_method = model.W_CompiledMethod(2)
        w_method.bytes = pushConstantOneBytecode + bytecode
        shadow.installmethod("foo", w_method)
        interp = new_interpreter(bytecodes)
        interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = fakeliterals(space, "foo")
        interp.s_active_context().push(w_object)
        callerContext = interp.w_active_context()
        interp.step()
        assert interp.s_active_context().w_sender() == callerContext
        assert interp.s_active_context().stack() == []
        assert interp.w_active_context().as_methodcontext_get_shadow(space).w_receiver().is_same_object(w_object)
        assert interp.w_active_context().as_methodcontext_get_shadow(space).w_method().is_same_object(shadow.s_methoddict().methoddict["foo"])
        assert callerContext.as_context_get_shadow(space).stack() == []
        interp.step()
        interp.step()
        assert interp.w_active_context() == callerContext
        assert interp.s_active_context().stack() == [result]

def test_sendLiteralSelectorBytecode():
    w_class = mockclass(space, 0)
    w_object = w_class.as_class_get_shadow(space).new()
    sendBytecodesTest(w_class, w_object, sendLiteralSelectorBytecode(0))
        
def test_fibWithArgument():
    bytecode = ''.join(map(chr, [ 16, 119, 178, 154, 118, 164, 11, 112, 16, 118, 177, 224, 112, 16, 119, 177, 224, 176, 124 ]))
    shadow = mockclass(space, 0).as_class_get_shadow(space)
    method = model.W_CompiledMethod(len(bytecode))
    method.literalsize = 1
    method.bytes = bytecode
    method.argsize = 1
    method.tempsize = 1
    method.literals = fakeliterals(space, "fib:")
    shadow.installmethod("fib:", method)
    w_object = shadow.new()
    interp = new_interpreter(sendLiteralSelectorBytecode(16) + returnTopFromMethod)
    interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = fakeliterals(space, "fib:")
    interp.s_active_context().push(w_object)
    interp.s_active_context().push(space.wrap_int(8))
    result = interp.interpret()
    assert space.unwrap_int(result) == 34

def test_send_to_primitive():

    def test():
        interp = new_interpreter(sendLiteralSelectorBytecode(1 + 16))
        interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = fakeliterals(space, "foo", "sub")
        interp.s_active_context().push(space.wrap_int(50))
        interp.s_active_context().push(space.wrap_int(8))
        callerContext = interp.w_active_context()
        interp.step()
        assert interp.w_active_context() is callerContext
        assert len(interp.s_active_context().stack()) == 1
        w_result = interp.s_active_context().pop()
        assert space.unwrap_int(w_result) == 42
        
    run_with_faked_methods(
        [[space.w_SmallInteger, primitives.SUBTRACT,
          1, "sub"]],
        test)

def test_makePoint():
    interp = new_interpreter(pushConstantZeroBytecode +
                             pushConstantOneBytecode +
                             bytecodePrimMakePoint)
    interp.step()
    interp.step()
    interp.step()
    w_point = interp.s_active_context().top()
    from pypy.lang.smalltalk.wrapper import PointWrapper
    point = PointWrapper(interp.space, w_point)
    assert point.x(interp.space) == 0
    assert point.y(interp.space) == 1

def test_longJumpIfTrue():
    interp = new_interpreter(longJumpIfTrue(0) + chr(15) + longJumpIfTrue(0) + chr(15))
    interp.s_active_context().push(space.w_false)
    pc = interp.s_active_context().pc() + 2
    interp.step()
    assert interp.s_active_context().pc() == pc
    interp.s_active_context().push(space.w_true)
    pc = interp.s_active_context().pc() + 2
    interp.step()
    assert interp.s_active_context().pc() == pc + 15

def test_longJumpIfFalse():
    interp = new_interpreter(pushConstantTrueBytecode + longJumpIfFalse(0) + chr(15) +
                             pushConstantFalseBytecode + longJumpIfFalse(0) + chr(15))
    interp.step()
    pc = interp.s_active_context().pc() + 2
    interp.step()
    assert interp.s_active_context().pc() == pc
    interp.step()
    pc = interp.s_active_context().pc() + 2
    interp.step()
    assert interp.s_active_context().pc() == pc + 15

def test_longUnconditionalJump():
    interp = new_interpreter(longUnconditionalJump(4) + chr(15))
    pc = interp.s_active_context().pc() + 2
    interp.step()
    assert interp.s_active_context().pc() == pc + 15

def test_shortUnconditionalJump():
    interp = new_interpreter(chr(145))
    pc = interp.s_active_context().pc() + 1
    interp.step()
    assert interp.s_active_context().pc() == pc + 2

def test_shortConditionalJump():
    interp = new_interpreter(pushConstantTrueBytecode + shortConditionalJump(3) +
                             pushConstantFalseBytecode + shortConditionalJump(3))
    interp.step()
    pc = interp.s_active_context().pc() + 1
    interp.step()
    assert interp.s_active_context().pc() == pc
    interp.step()
    pc = interp.s_active_context().pc() + 1
    interp.step()
    assert interp.s_active_context().pc() == pc + 4

def test_popStackBytecode():
    interp = new_interpreter(pushConstantTrueBytecode +
                             popStackBytecode)
    interp.step()
    assert interp.s_active_context().stack() == [space.w_true]
    interp.step()
    assert interp.s_active_context().stack() == []

def test_extendedPushBytecode():
    test_pushReceiverVariableBytecode(extendedPushBytecode + chr((0<<6) + 0) +
                                      extendedPushBytecode + chr((0<<6) + 1) +
                                      extendedPushBytecode + chr((0<<6) + 2))

    test_pushTemporaryVariableBytecode(extendedPushBytecode + chr((1<<6) + 0) +
                                       extendedPushBytecode + chr((1<<6) + 1) +
                                       extendedPushBytecode + chr((1<<6) + 2))

    test_pushLiteralConstantBytecode(extendedPushBytecode + chr((2<<6) + 0) +
                                     extendedPushBytecode + chr((2<<6) + 1) +
                                     extendedPushBytecode + chr((2<<6) + 2))

    test_pushLiteralVariableBytecode(extendedPushBytecode + chr((3<<6) + 0))

def storeAssociation(bytecode):
    w_association = mockclass(space, 2).as_class_get_shadow(space).new()
    w_association.store(space, 0, "mykey")
    w_association.store(space, 1, "myvalue")
    interp = new_interpreter(pushConstantOneBytecode + bytecode)
    interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = fakeliterals(space, w_association)
    interp.step()
    interp.step()
    assert w_association.fetch(space, 1).is_same_object(space.w_one)

def test_extendedStoreAndPopBytecode():
    test_storeAndPopReceiverVariableBytecode(lambda index: extendedStoreAndPopBytecode + chr((0<<6) + index))
                
    test_storeAndPopTemporaryVariableBytecode(lambda index: extendedStoreAndPopBytecode + chr((1<<6) + index))

    py.test.raises(interpreter.IllegalStoreError,
                   test_storeAndPopTemporaryVariableBytecode,
                   lambda index: extendedStoreAndPopBytecode + chr((2<<6) + index))

    storeAssociation(extendedStoreAndPopBytecode + chr((3<<6) + 0))

def test_callPrimitiveAndPush_fallback():
    interp = new_interpreter(bytecodePrimAdd)
    shadow = mockclass(space, 0).as_class_get_shadow(space)
    w_method = model.W_CompiledMethod(0)
    w_method.argsize = 1
    w_method.tempsize = 1
    w_method.literalsize = 1
    shadow.installmethod("+", w_method) 
    
    w_object = shadow.new()
    interp.s_active_context().push(w_object)
    interp.s_active_context().push(space.w_one)
    interp.step()
    assert interp.w_active_context().as_methodcontext_get_shadow(space).w_method() == shadow.s_methoddict().methoddict["+"]
    assert interp.s_active_context().w_receiver() is w_object
    assert interp.w_active_context().as_methodcontext_get_shadow(space).gettemp(0).is_same_object(space.w_one)
    assert interp.s_active_context().stack() == []

def test_bytecodePrimBool():
    interp = new_interpreter(bytecodePrimLessThan +
                             bytecodePrimGreaterThan +
                             bytecodePrimLessOrEqual +
                             bytecodePrimGreaterOrEqual +
                             bytecodePrimEqual +
                             bytecodePrimNotEqual)
    for i in range(6):
        interp.s_active_context().push(space.w_one)
        interp.s_active_context().push(space.w_two)
        interp.step()
    assert interp.s_active_context().stack() == [space.w_true, space.w_false,
                                          space.w_true, space.w_false,
                                          space.w_false, space.w_true]

def test_singleExtendedSendBytecode():
    w_class = mockclass(space, 0)
    w_object = w_class.as_class_get_shadow(space).new()
    sendBytecodesTest(w_class, w_object, singleExtendedSendBytecode + chr((0<<5)+0))

def test_singleExtendedSuperBytecode(bytecode=singleExtendedSuperBytecode + chr((0<<5) + 0)):
    w_supersuper = mockclass(space, 0)
    w_super = mockclass(space, 0, w_superclass=w_supersuper)
    w_class = mockclass(space, 0, w_superclass=w_super)
    w_object = w_class.as_class_get_shadow(space).new()
    # first call method installed in w_class
    bytecodes = singleExtendedSendBytecode + chr(0)
    # which does a call to its super
    meth1 = model.W_CompiledMethod(2)
    meth1.bytes = pushReceiverBytecode + bytecode
    w_class.as_class_get_shadow(space).installmethod("foo", meth1)
    # and that one again to its super
    meth2 = model.W_CompiledMethod(2)
    meth2.bytes = pushReceiverBytecode + bytecode
    w_super.as_class_get_shadow(space).installmethod("foo", meth2)
    meth3 = model.W_CompiledMethod(0)
    w_supersuper.as_class_get_shadow(space).installmethod("foo", meth3)
    meth1.literals = fakeliterals(space, "foo")
    meth2.literals = fakeliterals(space, "foo")
    interp = new_interpreter(bytecodes)
    interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = fakeliterals(space, "foo")
    interp.s_active_context().push(w_object)
    interp.step()
    for w_specificclass in [w_super, w_supersuper]:
        callerContext = interp.w_active_context()
        interp.step()
        interp.step()
        assert interp.s_active_context().w_sender() == callerContext
        assert interp.s_active_context().stack() == []
        assert interp.w_active_context().as_methodcontext_get_shadow(space).w_receiver() == w_object
        meth = w_specificclass.as_class_get_shadow(space).s_methoddict().methoddict["foo"]
        assert interp.w_active_context().as_methodcontext_get_shadow(space).w_method() == meth
        assert callerContext.as_context_get_shadow(space).stack() == []

def test_secondExtendedSendBytecode():
    w_class = mockclass(space, 0)
    w_object = w_class.as_class_get_shadow(space).new()
    sendBytecodesTest(w_class, w_object, secondExtendedSendBytecode + chr(0)) 

def test_doubleExtendedDoAnythinBytecode():
    w_class = mockclass(space, 0)
    w_object = w_class.as_class_get_shadow(space).new()

    sendBytecodesTest(w_class, w_object, doubleExtendedDoAnythingBytecode + chr((0<<5) + 0) + chr(0))

    test_singleExtendedSuperBytecode(doubleExtendedDoAnythingBytecode + (chr((1<<5) + 0) + chr(0)))

    test_pushReceiverVariableBytecode(doubleExtendedDoAnythingBytecode + chr(2<<5) + chr(0) +
                                      doubleExtendedDoAnythingBytecode + chr(2<<5) + chr(1) +
                                      doubleExtendedDoAnythingBytecode + chr(2<<5) + chr(2))

    test_pushLiteralConstantBytecode(doubleExtendedDoAnythingBytecode + chr(3<<5) + chr(0) +
                                     doubleExtendedDoAnythingBytecode + chr(3<<5) + chr(1) +
                                     doubleExtendedDoAnythingBytecode + chr(3<<5) + chr(2))

    test_pushLiteralVariableBytecode(doubleExtendedDoAnythingBytecode + chr(4<<5) + chr(0))

    test_storeAndPopReceiverVariableBytecode(lambda index: doubleExtendedDoAnythingBytecode + chr(5<<5) + chr(index), False)

    test_storeAndPopReceiverVariableBytecode(lambda index: doubleExtendedDoAnythingBytecode + chr(6<<5) + chr(index))

    storeAssociation(doubleExtendedDoAnythingBytecode + chr(7<<5) + chr(0))

def interpret_bc(bcodes, literals, receiver=space.w_nil):
    bcode = "".join([chr(x) for x in bcodes])
    interp = new_interpreter(bcode, receiver=receiver)
    interp.w_active_context().as_methodcontext_get_shadow(space).w_method().literals = literals
    return interp.interpret()

# tests: bytecodePrimValue & bytecodePrimValueWithArg
def test_bc_3_plus_4():
    # value0
    #   " (self >> #value0) byteCode "
    #   " (self >> #value0) literals "
    # 
    #   ^ [ 3 + 4 ] value
    assert interpret_bc(
        [ 137, 117, 200, 164, 4, 32, 33, 176, 125, 201, 124],
        fakeliterals(space, space.wrap_int(3), space.wrap_int(4))).value == 7


def test_bc_x_plus_x_plus_1():
    # value1
    #   " (self >> #value1) byteCode "
    #   " (self >> #value1) literals "
    # 
    #   ^ [ :x | x + x + 1 ] value: 3
    assert interpret_bc(
        [ 137, 118, 200, 164, 7, 104, 16, 16,
          176, 118, 176, 125, 32, 202, 124 ],
        fakeliterals(space, space.wrap_int(3))).value == 7

def test_bc_x_plus_y():
    # value2
    #   " (self >> #value2) byteCode "
    #   " (self >> #value2) literals "
    # 
    #   ^ [ :x :y | x + y ] value: 3 value: 4

    def test():
        assert interpret_bc(
            [ 137, 119, 200, 164, 6, 105, 104, 16, 17,
              176, 125, 33, 34, 240, 124 ],
            fakeliterals(space, "value:value:", space.wrap_int(3), space.wrap_int(4))).value == 7
    run_with_faked_methods(
        [[space.w_BlockContext, primitives.PRIMITIVE_VALUE,
          2, "value:value:"]],
        test)

def test_bc_push_rcvr_in_block():
    # value1
    #   " (self >> #value1) byteCode "
    #   " (self >> #value1) literals "
    # 
    #   ^ [ self ] value
    assert interpret_bc(
        [ 137, 117, 200, 164, 2, 112, 125, 201, 124 ],
        fakeliterals(space, space.wrap_int(3))) is space.w_nil

def test_bc_value_return():
    # valueReturn
    #   " (self >> #value1) byteCode "
    #   " (self >> #value1) literals "
    # 
    #   [ ^ 1 ] value. ^ 2
    assert interpret_bc(
        [ 137, 117, 200, 164, 2, 118, 124, 201, 135, 119, 124 ],
        fakeliterals(space, )).value == 1

def test_bc_value_with_args():
    # valueWithArgs
    #   " (self >> #value1) byteCode "
    #   " (self >> #value1) literals "
    # 
    #   [ :a :b | a - b ] valueWithArguments: #(3 2)
    def test():
        assert interpret_bc(
            [ 137, 119, 200, 164, 6,
              105, 104, 16, 17, 177,
              125, 33, 224, 124 ],
            fakeliterals(space, "valueWithArguments:",
                         [3, 2])).value == 1
    run_with_faked_methods(
        [[space.w_BlockContext, primitives.PRIMITIVE_VALUE_WITH_ARGS,
          1, "valueWithArguments:"]],
        test)

def test_bc_primBytecodeAt_string():
    #   ^ 'a' at: 1
    def test():
        assert interpret_bc(
            [ 32, 118, 192, 124],
            fakeliterals(space, "a")) == space.wrap_char("a")
    run_with_faked_methods(
        [[space.w_String, primitives.STRING_AT, 1, "at:"]],
        test)
    
def test_bc_primBytecodeAtPut_string():
    #   ^ 'a' at: 1 put:'b'
    def test():
        assert interpret_bc(
            [ 32, 118, 33, 193, 124 ],
            fakeliterals(space, "a", space.wrap_char("b"))) == space.wrap_char("b")
    run_with_faked_methods(
        [[space.w_String, primitives.STRING_AT_PUT, 2, "at:put:"]],
        test)

def test_bc_primBytecodeAt_with_instvars():
    #   ^ self at: 1
    w_fakeclass = mockclass(space, 1, name='fakeclass', varsized=True)
    w_fakeinst = w_fakeclass.as_class_get_shadow(space).new(1)
    w_fakeinst.store(space, 0, space.wrap_char("a")) # static slot 0: instance variable
    w_fakeinst.store(space, 1, space.wrap_char("b")) # varying slot 1
    def test():
        assert space.unwrap_char(interpret_bc(
            [112, 118, 192, 124],
            fakeliterals(space, ),
            receiver=w_fakeinst)) == "b"
    run_with_faked_methods(
        [[w_fakeclass, primitives.AT, 1, "at:"]],
        test)

def test_bc_primBytecodeAtPut_with_instvars():
    #   ^ self at: 1 put: #b
    w_fakeclass = mockclass(space, 1, name='fakeclass', varsized=True)
    w_fakeinst = w_fakeclass.as_class_get_shadow(space).new(1)
    w_fakeinst.store(space, 0, space.wrap_char("a")) # static slot 0: instance variable
    w_fakeinst.store(space, 1, space.wrap_char("a")) # varying slot 1
    def test():
        assert space.unwrap_char(interpret_bc(
            [0x70, 0x76, 0x20, 0xc1, 0x7c],
            fakeliterals(space, space.wrap_char("b")),
            receiver=w_fakeinst)) == "b"
        assert space.unwrap_char(w_fakeinst.fetch(space, 0)) == "a"
        assert space.unwrap_char(w_fakeinst.fetch(space, 1)) == "b"
    run_with_faked_methods(
        [[w_fakeclass, primitives.AT_PUT, 2, "at:put:"]],
        test)

def test_bc_objectAtAndAtPut():
    #   ^ self objectAt: 1.          yields the method header
    #   ^ self objectAt: 2.          yields the first literal (22)
    #   ^ self objectAt: 2 put: 3.   changes the first literal to 3
    #   ^ self objectAt: 2.          yields the new first literal (3)
    prim_meth = model.W_CompiledMethod(header=1024)
    prim_meth.literals = fakeliterals(space, 22)
    oal = fakeliterals(space, "objectAt:")
    oalp = fakeliterals(space, "objectAt:put:", 3)
    def test():
        assert interpret_bc(
            [112, 118, 224, 124], oal, receiver=prim_meth).value == 1024
        assert interpret_bc(
            [112, 119, 224, 124], oal, receiver=prim_meth).value == 22
        assert interpret_bc(
            [112, 119, 33, 240, 124], oalp, receiver=prim_meth).value == 3
        assert interpret_bc(
            [112, 119, 224, 124], oal, receiver=prim_meth).value == 3
    run_with_faked_methods(
        [[space.w_CompiledMethod, primitives.OBJECT_AT, 1, "objectAt:"],
         [space.w_CompiledMethod, primitives.OBJECT_AT_PUT, 2, "objectAt:put:"]],
        test)

def test_runwithtrace():
    # We run random tests with the bc_trace option turned on explicitely
    from pypy.lang.smalltalk.conftest import option
    bc_trace = option.bc_trace
    option.bc_trace = True
    test_storeAndPopReceiverVariableBytecode()
    test_bc_objectAtAndAtPut()
    option.bc_trace = bc_trace
