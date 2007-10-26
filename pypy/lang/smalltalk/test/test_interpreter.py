import py
from pypy.lang.smalltalk import model, interpreter, primitives, shadow
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk.objtable import wrap_int
import pypy.lang.smalltalk.classtable as ct

mockclass = ct.bootstrap_class

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
        s_class = w_class.as_class_get_shadow()
        prim_meth = model.W_CompiledMethod(
            0, "", argsize=argsize, primitive=primnum)
        s_class.installmethod(methname, prim_meth)
        
    try:
        func()
    finally:
        # Uninstall those methods:
        for (w_class, _, _, methname) in methods:
            s_class = w_class.as_class_get_shadow()
            del s_class.methoddict[methname]

def fakesymbol(s, _cache={}):
    try:
        return _cache[s]
    except KeyError:
        result = _cache[s] = objtable.wrap_string(s)
        return result

def fakeliterals(*literals):
    def fakeliteral(lit):
        if isinstance(lit, str):
            return fakesymbol(lit)
        elif isinstance(lit, int):
            return wrap_int(lit)
        elif isinstance(lit, list):
            lstlen = len(lit)
            res = ct.w_Array.as_class_get_shadow().new(lstlen)
            for i in range(lstlen):
                res.storevarpointer(i, fakeliteral(lit[i]))
            return res
        return lit
        
    return ["methodheader"] + [fakeliteral(lit) for lit in literals]

def new_interpreter(bytes, receiver=objtable.w_nil):
    assert isinstance(bytes, str)
    w_method = model.W_CompiledMethod(0, bytes=bytes,
                                      argsize=2, tempsize=1)
    w_frame = w_method.create_frame(receiver, ["foo", "bar"])
    interp = interpreter.Interpreter()
    interp.w_active_context = w_frame
    return interp

def test_create_frame():
    w_method = model.W_CompiledMethod(0, bytes="hello",
                                      argsize=2, tempsize=1)
    w_frame = w_method.create_frame("receiver", ["foo", "bar"])
    assert w_frame.w_receiver == "receiver"
    assert w_frame.gettemp(0) == "foo"
    assert w_frame.gettemp(1) == "bar"
    assert w_frame.gettemp(2) == None
    w_frame.settemp(2, "spam")
    assert w_frame.gettemp(2) == "spam"
    assert w_frame.getNextBytecode() == ord("h")
    assert w_frame.getNextBytecode() == ord("e")
    assert w_frame.getNextBytecode() == ord("l")

def test_push_pop():
    interp = new_interpreter("")
    frame = interp.w_active_context
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
    assert interp.w_active_context.top() == interp.w_active_context.w_receiver

def test_pushReceiverVariableBytecode(bytecode = (pushReceiverVariableBytecode(0) +
                                                  pushReceiverVariableBytecode(1) +
                                                  pushReceiverVariableBytecode(2))):
    w_demo = mockclass(3).as_class_get_shadow().new()
    w_demo.store(0, "egg")
    w_demo.store(1, "bar")
    w_demo.store(2, "baz")
    interp = new_interpreter(bytecode, receiver = w_demo)
    interp.step()
    interp.step()
    interp.step()
    assert interp.w_active_context.stack == ["egg", "bar", "baz"]

def test_pushTemporaryVariableBytecode(bytecode=(pushTemporaryVariableBytecode(0) +
                                                 pushTemporaryVariableBytecode(1) +
                                                 pushTemporaryVariableBytecode(2))):
    interp = new_interpreter(bytecode)
    interp.w_active_context.settemp(2, "temp")
    interp.step()
    interp.step()
    interp.step()
    assert interp.w_active_context.stack == ["foo", "bar", "temp"]

def test_pushLiteralConstantBytecode(bytecode=pushLiteralConstantBytecode(0) +
                                              pushLiteralConstantBytecode(1) +
                                              pushLiteralConstantBytecode(2)):
    interp = new_interpreter(bytecode)
    interp.w_active_context.w_method().literals = fakeliterals("a", "b", "c")
    interp.step()
    interp.step()
    interp.step()
    assert interp.w_active_context.stack == [fakesymbol("a"),
                                             fakesymbol("b"),
                                             fakesymbol("c")]

def test_pushLiteralVariableBytecode(bytecode=pushLiteralVariableBytecode(0)):
    w_association = mockclass(2).as_class_get_shadow().new()
    w_association.store(0, "mykey")
    w_association.store(1, "myvalue")
    interp = new_interpreter(bytecode)
    interp.w_active_context.w_method().literals = fakeliterals(w_association)
    interp.step()
    assert interp.w_active_context.stack == ["myvalue"]

def test_storeAndPopReceiverVariableBytecode(bytecode=storeAndPopReceiverVariableBytecode,
                                             popped=True):
    shadow = mockclass(8).as_class_get_shadow()
    for index in range(8):
        w_object = shadow.new()
        interp = new_interpreter(pushConstantTrueBytecode + bytecode(index))
        interp.w_active_context.w_receiver = w_object
        interp.step()
        interp.step()
        if popped:
            assert interp.w_active_context.stack == []
        else:
            assert interp.w_active_context.stack == [interp.TRUE]

        for test_index in range(8):
            if test_index == index:
                assert w_object.fetch(test_index) == interp.TRUE
            else:
                assert w_object.fetch(test_index) == None

def test_storeAndPopTemporaryVariableBytecode(bytecode=storeAndPopTemporaryVariableBytecode):
    for index in range(8):
        interp = new_interpreter(pushConstantTrueBytecode + bytecode(index))
        interp.w_active_context.temps = [None] * 8
        interp.step()
        interp.step()
        assert interp.w_active_context.stack == []
        for test_index in range(8):
            if test_index == index:
                assert interp.w_active_context.temps[test_index] == interp.TRUE
            else:
                assert interp.w_active_context.temps[test_index] == None
    

def test_pushConstantTrueBytecode():
    interp = new_interpreter(pushConstantTrueBytecode)
    interp.step()
    assert interp.w_active_context.top() == interp.TRUE

def test_pushConstantFalseBytecode():
    interp = new_interpreter(pushConstantFalseBytecode)
    interp.step()
    assert interp.w_active_context.top() == interp.FALSE

def test_pushConstantNilBytecode():
    interp = new_interpreter(pushConstantNilBytecode)
    interp.step()
    assert interp.w_active_context.top() == interp.NIL

def test_pushConstantMinusOneBytecode():
    interp = new_interpreter(pushConstantMinusOneBytecode)
    interp.step()
    assert interp.w_active_context.top() == interp.MONE

def test_pushConstantZeroBytecode():
    interp = new_interpreter(pushConstantZeroBytecode)
    interp.step()
    assert interp.w_active_context.top() == interp.ZERO
    
def test_pushConstantOneBytecode():
    interp = new_interpreter(pushConstantOneBytecode)
    interp.step()
    assert interp.w_active_context.top() == interp.ONE

def test_pushConstantTwoBytecode():
    interp = new_interpreter(pushConstantTwoBytecode)
    interp.step()
    assert interp.w_active_context.top()

def test_pushActiveContextBytecode():
    interp = new_interpreter(pushActiveContextBytecode)
    interp.step()
    assert interp.w_active_context.top() == interp.w_active_context
    
def test_duplicateTopBytecode():
    interp = new_interpreter(pushConstantZeroBytecode + duplicateTopBytecode)
    interp.step()
    interp.step()
    assert interp.w_active_context.stack == [interp.ZERO, interp.ZERO]

# w_class - the class from which the method is going to be called
# (and on which it is going to be installed)
# w_object - the actual object we will be sending the method to
# bytecodes - the bytecode to be executed
def sendBytecodesTest(w_class, w_object, bytecodes):
    for bytecode, result in [ (returnReceiver, w_object), 
          (returnTrue, interpreter.Interpreter.TRUE), 
          (returnFalse, interpreter.Interpreter.FALSE),
          (returnNil, interpreter.Interpreter.NIL),
          (returnTopFromMethod, interpreter.Interpreter.ONE) ]:
        shadow = w_class.as_class_get_shadow()
        shadow.installmethod("foo",
             model.W_CompiledMethod(0, pushConstantOneBytecode + bytecode))
        interp = new_interpreter(bytecodes)
        interp.w_active_context.w_method().literals = fakeliterals("foo")
        interp.w_active_context.push(w_object)
        callerContext = interp.w_active_context
        interp.step()
        assert interp.w_active_context.w_sender == callerContext
        assert interp.w_active_context.stack == []
        assert interp.w_active_context.w_receiver == w_object
        assert interp.w_active_context.w_method() == shadow.methoddict["foo"]
        assert callerContext.stack == []
        interp.step()
        interp.step()
        assert interp.w_active_context == callerContext
        assert interp.w_active_context.stack == [result]

def test_sendLiteralSelectorBytecode():
    w_class = mockclass(0)
    w_object = w_class.as_class_get_shadow().new()
    sendBytecodesTest(w_class, w_object, sendLiteralSelectorBytecode(0))
        
def test_fibWithArgument():
    bytecode = ''.join(map(chr, [ 16, 119, 178, 154, 118, 164, 11, 112, 16, 118, 177, 224, 112, 16, 119, 177, 224, 176, 124 ]))
    shadow = mockclass(0).as_class_get_shadow()
    method = model.W_CompiledMethod(1, bytecode, 1)
    method.literals = fakeliterals("fib:")
    shadow.installmethod("fib:", method)
    w_object = shadow.new()
    interp = new_interpreter(sendLiteralSelectorBytecode(16) + returnTopFromMethod)
    interp.w_active_context.w_method().literals = fakeliterals("fib:")
    interp.w_active_context.push(w_object)
    interp.w_active_context.push(wrap_int(8))
    result = interp.interpret()
    assert primitives.unwrap_int(result) == 34

def test_send_to_primitive():

    def test():
        interp = new_interpreter(sendLiteralSelectorBytecode(1 + 16))
        interp.w_active_context.w_method().literals = fakeliterals("foo", "sub")
        interp.w_active_context.push(wrap_int(50))
        interp.w_active_context.push(wrap_int(8))
        callerContext = interp.w_active_context
        interp.step()
        assert interp.w_active_context is callerContext
        assert len(interp.w_active_context.stack) == 1
        w_result = interp.w_active_context.pop()
        assert primitives.unwrap_int(w_result) == 42
        
    run_with_faked_methods(
        [[ct.w_SmallInteger, primitives.SUBTRACT,
          1, "sub"]],
        test)

def test_longJumpIfTrue():
    interp = new_interpreter(longJumpIfTrue(0) + chr(15) + longJumpIfTrue(0) + chr(15))
    interp.w_active_context.push(interp.FALSE)
    pc = interp.w_active_context.pc + 2
    interp.step()
    assert interp.w_active_context.pc == pc
    interp.w_active_context.push(interp.TRUE)
    pc = interp.w_active_context.pc + 2
    interp.step()
    assert interp.w_active_context.pc == pc + 15

def test_longJumpIfFalse():
    interp = new_interpreter(pushConstantTrueBytecode + longJumpIfFalse(0) + chr(15) +
                             pushConstantFalseBytecode + longJumpIfFalse(0) + chr(15))
    interp.step()
    pc = interp.w_active_context.pc + 2
    interp.step()
    assert interp.w_active_context.pc == pc
    interp.step()
    pc = interp.w_active_context.pc + 2
    interp.step()
    assert interp.w_active_context.pc == pc + 15

def test_longUnconditionalJump():
    interp = new_interpreter(longUnconditionalJump(4) + chr(15))
    pc = interp.w_active_context.pc + 2
    interp.step()
    assert interp.w_active_context.pc == pc + 15

def test_shortUnconditionalJump():
    interp = new_interpreter(chr(145))
    pc = interp.w_active_context.pc + 1
    interp.step()
    assert interp.w_active_context.pc == pc + 2

def test_shortConditionalJump():
    interp = new_interpreter(pushConstantTrueBytecode + shortConditionalJump(3) +
                             pushConstantFalseBytecode + shortConditionalJump(3))
    interp.step()
    pc = interp.w_active_context.pc + 1
    interp.step()
    assert interp.w_active_context.pc == pc
    interp.step()
    pc = interp.w_active_context.pc + 1
    interp.step()
    assert interp.w_active_context.pc == pc + 4

def test_popStackBytecode():
    interp = new_interpreter(pushConstantTrueBytecode +
                             popStackBytecode)
    interp.step()
    assert interp.w_active_context.stack == [interp.TRUE]
    interp.step()
    assert interp.w_active_context.stack == []

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
    w_association = mockclass(2).as_class_get_shadow().new()
    w_association.store(0, "mykey")
    w_association.store(1, "myvalue")
    interp = new_interpreter(pushConstantOneBytecode + bytecode)
    interp.w_active_context.w_method().literals = fakeliterals(w_association)
    interp.step()
    interp.step()
    assert w_association.fetch(1) == interp.ONE

def test_extendedStoreAndPopBytecode():
    test_storeAndPopReceiverVariableBytecode(lambda index: extendedStoreAndPopBytecode + chr((0<<6) + index))
                
    test_storeAndPopTemporaryVariableBytecode(lambda index: extendedStoreAndPopBytecode + chr((1<<6) + index))

    py.test.raises(interpreter.IllegalStoreError,
                   test_storeAndPopTemporaryVariableBytecode,
                   lambda index: extendedStoreAndPopBytecode + chr((2<<6) + index))

    storeAssociation(extendedStoreAndPopBytecode + chr((3<<6) + 0))

def test_callPrimitiveAndPush_fallback():
    interp = new_interpreter(bytecodePrimAdd)
    shadow = mockclass(0).as_class_get_shadow()
    shadow.installmethod("+", model.W_CompiledMethod(1, "", 1))
    w_object = shadow.new()
    interp.w_active_context.push(w_object)
    interp.w_active_context.push(interp.ONE)
    interp.step()
    assert interp.w_active_context.w_method() == shadow.methoddict["+"]
    assert interp.w_active_context.w_receiver is w_object
    assert interp.w_active_context.gettemp(0) == interp.ONE
    assert interp.w_active_context.stack == []

def test_bytecodePrimBool():
    interp = new_interpreter(bytecodePrimLessThan +
                             bytecodePrimGreaterThan +
                             bytecodePrimLessOrEqual +
                             bytecodePrimGreaterOrEqual +
                             bytecodePrimEqual +
                             bytecodePrimNotEqual)
    for i in range(6):
        interp.w_active_context.push(interp.ONE)
        interp.w_active_context.push(interp.TWO)
        interp.step()
    assert interp.w_active_context.stack == [interp.TRUE, interp.FALSE,
                                          interp.TRUE, interp.FALSE,
                                          interp.FALSE, interp.TRUE]

def test_singleExtendedSendBytecode():
    w_class = mockclass(0)
    w_object = w_class.as_class_get_shadow().new()
    sendBytecodesTest(w_class, w_object, singleExtendedSendBytecode + chr((0<<5)+0))

def test_singleExtendedSuperBytecode(bytecode=singleExtendedSuperBytecode + chr((0<<5) + 0)):
    w_supersuper = mockclass(0)
    w_super = mockclass(0, w_superclass=w_supersuper)
    w_class = mockclass(0, w_superclass=w_super)
    w_object = w_class.as_class_get_shadow().new()
    # first call method installed in w_class
    bytecodes = singleExtendedSendBytecode + chr(0)
    # which does a call to its super
    meth1 = model.W_CompiledMethod(0, pushReceiverBytecode + bytecode)
    w_class.as_class_get_shadow().installmethod("foo", meth1)
    # and that one again to its super
    meth2 = model.W_CompiledMethod(0, pushReceiverBytecode + bytecode)
    w_super.as_class_get_shadow().installmethod("foo", meth2)
    meth3 = model.W_CompiledMethod(0, "")
    w_supersuper.as_class_get_shadow().installmethod("foo", meth3)
    meth1.literals = fakeliterals("foo")
    meth2.literals = fakeliterals("foo")
    interp = new_interpreter(bytecodes)
    interp.w_active_context.w_method().literals = fakeliterals("foo")
    interp.w_active_context.push(w_object)
    interp.step()
    for w_specificclass in [w_super, w_supersuper]:
        callerContext = interp.w_active_context
        interp.step()
        interp.step()
        assert interp.w_active_context.w_sender == callerContext
        assert interp.w_active_context.stack == []
        assert interp.w_active_context.w_receiver == w_object
        meth = w_specificclass.as_class_get_shadow().methoddict["foo"]
        assert interp.w_active_context.w_method() == meth
        assert callerContext.stack == []

def test_secondExtendedSendBytecode():
    w_class = mockclass(0)
    w_object = w_class.as_class_get_shadow().new()
    sendBytecodesTest(w_class, w_object, secondExtendedSendBytecode + chr(0)) 

def test_doubleExtendedDoAnythinBytecode():
    w_class = mockclass(0)
    w_object = w_class.as_class_get_shadow().new()

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

def interpret_bc(bcodes, literals):
    bcode = "".join([chr(x) for x in bcodes])
    interp = new_interpreter(bcode)
    interp.w_active_context.w_method().literals = literals
    return interp.interpret()

def test_bc_3_plus_4():
    # value0
    # 	" (self >> #value0) byteCode "
    # 	" (self >> #value0) literals "
    # 
    # 	^ [ 3 + 4 ] value
    assert interpret_bc(
        [ 137, 117, 200, 164, 4, 32, 33, 176, 125, 201, 124],
        fakeliterals(wrap_int(3), wrap_int(4))).value == 7


def test_bc_x_plus_x_plus_1():
    # value1
    # 	" (self >> #value1) byteCode "
    # 	" (self >> #value1) literals "
    # 
    # 	^ [ :x | x + x + 1 ] value: 3
    assert interpret_bc(
        [ 137, 118, 200, 164, 7, 104, 16, 16,
          176, 118, 176, 125, 32, 202, 124 ],
        fakeliterals(wrap_int(3))).value == 7

def test_bc_x_plus_y():
    # value2
    # 	" (self >> #value2) byteCode "
    # 	" (self >> #value2) literals "
    # 
    # 	^ [ :x :y | x + y ] value: 3 value: 4

    def test():
        assert interpret_bc(
            [ 137, 119, 200, 164, 6, 105, 104, 16, 17,
              176, 125, 33, 34, 240, 124 ],
            fakeliterals("value:value:", wrap_int(3), wrap_int(4))).value == 7
    run_with_faked_methods(
        [[ct.w_BlockContext, primitives.PRIMITIVE_VALUE,
          2, "value:value:"]],
        test)

def test_bc_push_rcvr_in_block():
    # value1
    # 	" (self >> #value1) byteCode "
    # 	" (self >> #value1) literals "
    # 
    # 	^ [ self ] value
    assert interpret_bc(
        [ 137, 117, 200, 164, 2, 112, 125, 201, 124 ],
        fakeliterals(wrap_int(3))) is objtable.w_nil

def test_bc_value_return():
    # valueReturn
    # 	" (self >> #value1) byteCode "
    # 	" (self >> #value1) literals "
    # 
    # 	[ ^ 1 ] value. ^ 2
    assert interpret_bc(
        [ 137, 117, 200, 164, 2, 118, 124, 201, 135, 119, 124 ],
        fakeliterals()).value == 1

def test_bc_value_with_args():
    # valueWithArgs
    # 	" (self >> #value1) byteCode "
    # 	" (self >> #value1) literals "
    # 
    # 	[ :a :b | a - b ] valueWithArguments: #(3 2)
    def test():
        assert interpret_bc(
            [ 137, 119, 200, 164, 6,
              105, 104, 16, 17, 177,
              125, 33, 224, 124 ],
            fakeliterals("valueWithArguments:",
                         [3, 2])).value == 1
    run_with_faked_methods(
        [[ct.w_BlockContext, primitives.PRIMITIVE_VALUE_WITH_ARGS,
          1, "valueWithArguments:"]],
        test)

