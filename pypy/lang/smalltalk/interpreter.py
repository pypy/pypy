import py
from pypy.lang.smalltalk import model, constants, primitives
from pypy.lang.smalltalk import objtable


class MissingBytecode(NotImplementedError):
    """Bytecode not implemented yet."""

class IllegalStoreError(Exception):
    """Illegal Store."""


class W_MethodContext(model.W_AbstractObjectWithIdentityHash):
    def __init__(self, method, receiver, arguments, sender = None):
        self.method = method
        self.receiver = receiver
        self.sender = sender
        self.stack = []
        self.temps = arguments + [None] * method.tempsize
        self.pc = 0

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_MethodContext
        return w_MethodContext

    def pop(self):
        return self.stack.pop()

    def push(self, w_v):
        self.stack.append(w_v)

    def top(self):
        return self.peek(0)
        
    def peek(self, idx):
        return self.stack[-(idx+1)]

    def pop_n(self, n):
        self.stack = self.stack[:len(self.stack)-n]
    
    def getByte(self):
        bytecode = self.method.bytes[self.pc]
        currentBytecode = ord(bytecode)
        self.pc = self.pc + 1
        return currentBytecode

    def getNextBytecode(self):
        self.currentBytecode = self.getByte()
        return self.currentBytecode

    def gettemp(self, index):
        return self.temps[index]

    def settemp(self, index, w_value):
        self.temps[index] = w_value

    # push bytecodes
    def pushReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.receiver.fetch(index))

    def pushTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.gettemp(index))

    def pushLiteralConstantBytecode(self, interp):
        index = self.currentBytecode & 31
        self.push(self.method.getliteral(index))

    def pushLiteralVariableBytecode(self, interp):
        # this bytecode assumes that literals[index] is an Association
        # which is an object with two named vars, and fetches the second
        # named var (the value).
        index = self.currentBytecode & 31
        association = self.method.getliteral(index)
        self.push(association.fetch(constants.ASSOCIATION_VALUE_INDEX))

    def storeAndPopReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.receiver.store(index, self.pop())

    def storeAndPopTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.settemp(index, self.pop())

    # push bytecodes
    def pushReceiverBytecode(self, interp):
        self.push(self.receiver)

    def pushConstantTrueBytecode(self, interp):
        self.push(interp.TRUE)

    def pushConstantFalseBytecode(self, interp):
        self.push(interp.FALSE)

    def pushConstantNilBytecode(self, interp):
        self.push(interp.NIL)

    def pushConstantMinusOneBytecode(self, interp):
        self.push(interp.MONE)

    def pushConstantZeroBytecode(self, interp):
        self.push(interp.ZERO)

    def pushConstantOneBytecode(self, interp):
        self.push(interp.ONE)

    def pushConstantTwoBytecode(self, interp):
        self.push(interp.TWO)
    
    def pushActiveContextBytecode(self, interp):
        self.push(self)

    def duplicateTopBytecode(self, interp):
        self.push(self.top())
    
    # send, return bytecodes
    def sendLiteralSelectorBytecode(self, interp):
        selector = self.method.getliteral(self.currentBytecode & 15)
        argcount = ((self.currentBytecode >> 4) & 3) - 1
        self._sendSelfSelector(selector, argcount, interp)
        
    def _sendSelfSelector(self, selector, argcount, interp):
        receiver = self.peek(argcount)
        self._sendSelector(selector, argcount, interp,
                           receiver, receiver.shadow_of_my_class())

    def _sendSuperSelector(self, selector, argcount, interp):
        s_compiledin = self.method.w_compiledin.as_class_get_shadow()
        self._sendSelector(selector, argcount, interp, self.receiver,
                           s_compiledin.s_superclass)

    def _sendSelector(self, selector, argcount, interp,
                      receiver, receiverclassshadow):
        method = receiverclassshadow.lookup(selector)
        assert method
        if method.primitive:
            func = primitives.prim_table[method.primitive]
            try:
                w_result = func(primitives.Args(interp, argcount))
            except primitives.PrimitiveFailedError:
                pass # ignore this error and fall back to the Smalltalk version
            else:
                # the primitive succeeded
                self.push(w_result)
                return
        arguments = self.stack[len(self.stack)-argcount:]
        interp.w_active_context = method.createFrame(receiver, arguments, self)
        self.pop_n(argcount + 1)

    def _return(self, object, interp):
        if self.sender is None:   # for tests, when returning from the top-level context
            raise ReturnFromTopLevel(object)
        self.sender.push(object)
        interp.w_active_context = self.sender

    def returnReceiver(self, interp):
        self._return(self.receiver, interp)

    def returnTrue(self, interp):
        self._return(interp.TRUE, interp)

    def returnFalse(self, interp):
        self._return(interp.FALSE, interp)

    def returnNil(self, interp):
        self._return(interp.NIL, interp)

    def returnTopFromMethod(self, interp):
        self._return(self.top(), interp)


    def returnTopFromBlock(self, interp):
        raise MissingBytecode

    def unknownBytecode(self, interp):
        raise MissingBytecode

    def extendedVariableTypeAndIndex(self):
        descriptor = self.getByte()
        return ((descriptor >> 6) & 3), (descriptor & 63)

    def extendedPushBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.push(self.receiver.fetch(variableIndex))
        elif variableType == 1:
            self.push(self.gettemp(variableIndex))
        elif variableType == 2:
            self.push(self.method.getliteral(variableIndex))
        elif variableType == 3:
            association = self.method.getliteral(variableIndex)
            self.push(association.fetch(constants.ASSOCIATION_VALUE_INDEX))

    def extendedStoreBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.receiver.store(variableIndex, self.top())
        elif variableType == 1:
            self.settemp(variableIndex, self.top())
        elif variableType == 2:
            raise IllegalStoreError
        elif variableType == 3:
            association = self.method.getliteral(variableIndex)
            association.store(constants.ASSOCIATION_VALUE_INDEX, self.top())

    def extendedStoreAndPopBytecode(self, interp):
        self.extendedStoreBytecode(interp)
        self.pop()

    def getExtendedSelectorArgcount(self):
        descriptor = self.getByte()
        return (self.method.getliteral(descriptor & 31)), (descriptor >> 5)

    def singleExtendedSendBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSelfSelector(selector, argcount, interp)

    def doubleExtendedDoAnythingBytecode(self, interp):
        second = self.getByte()
        third = self.getByte()
        opType = second >> 5
        if opType == 0:
            # selfsend
            self._sendSelfSelector(self.method.getliteral(third),
                                   second & 31, interp)
        elif opType == 1:
            # supersend
            self._sendSuperSelector(self.method.getliteral(third),
                                    second & 31, interp)
        elif opType == 2:
            # pushReceiver
            self.push(self.receiver.fetch(third))
        elif opType == 3:
            # pushLiteralConstant
            self.push(self.method.getliteral(third))
        elif opType == 4:
            # pushLiteralVariable
            association = self.method.getliteral(third)
            self.push(association.fetch(constants.ASSOCIATION_VALUE_INDEX))
        elif opType == 5:
            self.receiver.store(third, self.top())
        elif opType == 6:
            self.receiver.store(third, self.pop())
        elif opType == 7:
            association = self.method.getliteral(third)
            association.store(constants.ASSOCIATION_VALUE_INDEX, self.top())

    def singleExtendedSuperBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSuperSelector(selector, argcount, interp)

    def secondExtendedSendBytecode(self, interp):
        descriptor = self.getByte()
        selector = self.method.getliteral(descriptor & 63)
        argcount = descriptor >> 6
        self._sendSelfSelector(selector, argcount, interp)

    def popStackBytecode(self, interp):
        self.pop()

    def experimentalBytecode(self, interp):
        raise MissingBytecode

    def jump(self,offset):
        self.pc = self.pc + offset

    def jumpConditional(self,bool,position):
        if self.top() == bool:
            self.jump(position)
        self.pop()

    def shortJumpPosition(self):
        return (self.currentBytecode & 7) + 1

    def shortUnconditionalJump(self, interp):
        self.jump(self.shortJumpPosition())

    def shortConditionalJump(self, interp):
        self.jumpConditional(interp.FALSE,self.shortJumpPosition())

    def longUnconditionalJump(self, interp):
        self.jump(self.longJumpPosition())

    def longJumpPosition(self):
        return ((self.currentBytecode & 3) << 8) + self.getNextBytecode()

    def longJumpIfTrue(self, interp):
        self.jumpConditional(interp.TRUE,self.longJumpPosition())

    def longJumpIfFalse(self, interp):
        self.jumpConditional(interp.FALSE,self.longJumpPosition())

    def callPrimitiveAndPush(self, primitive, selector,
                             argcount, interp):
        try:
            args = primitives.Args(interp, argcount)
            self.push(primitives.prim_table[primitive](args))
        except primitives.PrimitiveFailedError:
            self._sendSelfSelector(selector, argcount, interp)

    def bytecodePrimAdd(self, interp):
        self.callPrimitiveAndPush(primitives.ADD, "+", 1, interp)

    def bytecodePrimSubtract(self, interp):
        self.callPrimitiveAndPush(primitives.SUBTRACT, "-", 1, interp)

    def bytecodePrimLessThan(self, interp):        
        self.callPrimitiveAndPush(primitives.LESSTHAN, "<", 1, interp)

    def bytecodePrimGreaterThan(self, interp):
        self.callPrimitiveAndPush(primitives.GREATERTHAN, ">", 1, interp)

    def bytecodePrimLessOrEqual(self, interp):
        self.callPrimitiveAndPush(primitives.LESSOREQUAL, "<=", 1, interp)

    def bytecodePrimGreaterOrEqual(self, interp):
        self.callPrimitiveAndPush(primitives.GREATEROREQUAL, ">=", 1, interp)

    def bytecodePrimEqual(self, interp):
        self.callPrimitiveAndPush(primitives.EQUAL, "=", 1, interp)

    def bytecodePrimNotEqual(self, interp):
        self.callPrimitiveAndPush(primitives.NOTEQUAL, "~=", 1, interp)

    def bytecodePrimMultiply(self, interp):
        self.callPrimitiveAndPush(primitives.MULTIPLY, "*", 1, interp)

    def bytecodePrimDivide(self, interp):
        self.callPrimitiveAndPush(primitives.DIVIDE, "/", 1, interp)

    def bytecodePrimMod(self, interp):
        self.callPrimitiveAndPush(primitives.MOD, "\\", 1, interp)

    def bytecodePrimMakePoint(self, interp):
        raise MissingBytecode

    def bytecodePrimBitShift(self, interp):
        self.callPrimitiveAndPush(primitives.BIT_SHIFT, "bitShift:", 1, interp)

    def bytecodePrimDiv(self, interp):
        self.callPrimitiveAndPush(primitives.DIV, "//", 1, interp)

    def bytecodePrimBitAnd(self, interp):
        self.callPrimitiveAndPush(primitives.BIT_AND, "&", 1, interp)

    def bytecodePrimBitOr(self, interp):
        self.callPrimitiveAndPush(primitives.BIT_OR, "|", 1, interp)

    def bytecodePrimAt(self, interp):
        self.callPrimitiveAndPush(primitives.AT, "at:", 1, interp)

    def bytecodePrimAtPut(self, interp):
        self.callPrimitiveAndPush(primitives.AT_PUT, "at:put:", 2, interp)

    def bytecodePrimSize(self, interp):
        self.callPrimitiveAndPush(primitives.SIZE, "size", 0, interp)

    def bytecodePrimNext(self, interp):
        raise MissingBytecode

    def bytecodePrimNextPut(self, interp):
        raise MissingBytecode

    def bytecodePrimAtEnd(self, interp):
        raise MissingBytecode

    def bytecodePrimEquivalent(self, interp):
        raise MissingBytecode

    def bytecodePrimClass(self, interp):
        raise MissingBytecode

    def bytecodePrimBlockCopy(self, interp):
        raise MissingBytecode

    def bytecodePrimValue(self, interp):
        raise MissingBytecode

    def bytecodePrimValueWithArg(self, interp):
        raise MissingBytecode

    def bytecodePrimDo(self, interp):
        self._sendSelfSelector("do:", 1, interp)

    def bytecodePrimNew(self, interp):
        self.callPrimitiveAndPush(primitives.NEW, "new", 0, interp)

    def bytecodePrimNewWithArg(self, interp):
        self.callPrimitiveAndPush(primitives.NEW_WITH_ARG, "new:", 1, interp)

    def bytecodePrimPointX(self, interp):
        self._sendSelfSelector("x", 0, interp)

    def bytecodePrimPointY(self, interp):
        self._sendSelfSelector("y", 0, interp)


class Interpreter:

    TRUE = objtable.w_true
    FALSE = objtable.w_false
    NIL = objtable.w_nil
    MONE = objtable.w_mone
    ZERO = objtable.w_zero
    ONE = objtable.w_one
    TWO = objtable.w_two
    
    def __init__(self):
        self.w_active_context = None

   
    def interpret(self):
        try:
            while True:
                self.step()
        except ReturnFromTopLevel, e:
            return e.object

    def step(self):
        next = self.w_active_context.getNextBytecode()
        bytecodeimpl = BYTECODE_TABLE[next]
        bytecodeimpl(self.w_active_context, self)
        
class ReturnFromTopLevel(Exception):
    def __init__(self, object):
        self.object = object

BYTECODE_RANGES = [
            (  0,  15, W_MethodContext.pushReceiverVariableBytecode),
            ( 16,  31, W_MethodContext.pushTemporaryVariableBytecode),
            ( 32,  63, W_MethodContext.pushLiteralConstantBytecode),
            ( 64,  95, W_MethodContext.pushLiteralVariableBytecode),
            ( 96, 103, W_MethodContext.storeAndPopReceiverVariableBytecode),
            (104, 111, W_MethodContext.storeAndPopTemporaryVariableBytecode),
            (112, W_MethodContext.pushReceiverBytecode),
            (113, W_MethodContext.pushConstantTrueBytecode),
            (114, W_MethodContext.pushConstantFalseBytecode),
            (115, W_MethodContext.pushConstantNilBytecode),
            (116, W_MethodContext.pushConstantMinusOneBytecode),
            (117, W_MethodContext.pushConstantZeroBytecode),
            (118, W_MethodContext.pushConstantOneBytecode),
            (119, W_MethodContext.pushConstantTwoBytecode),
            (120, W_MethodContext.returnReceiver),
            (121, W_MethodContext.returnTrue),
            (122, W_MethodContext.returnFalse),
            (123, W_MethodContext.returnNil),
            (124, W_MethodContext.returnTopFromMethod),
            (125, W_MethodContext.returnTopFromBlock),
            (126, W_MethodContext.unknownBytecode),
            (127, W_MethodContext.unknownBytecode),
            (128, W_MethodContext.extendedPushBytecode),
            (129, W_MethodContext.extendedStoreBytecode),
            (130, W_MethodContext.extendedStoreAndPopBytecode),
            (131, W_MethodContext.singleExtendedSendBytecode),
            (132, W_MethodContext.doubleExtendedDoAnythingBytecode),
            (133, W_MethodContext.singleExtendedSuperBytecode),
            (134, W_MethodContext.secondExtendedSendBytecode),
            (135, W_MethodContext.popStackBytecode),
            (136, W_MethodContext.duplicateTopBytecode),
            (137, W_MethodContext.pushActiveContextBytecode),
            (138, 143, W_MethodContext.experimentalBytecode),
            (144, 151, W_MethodContext.shortUnconditionalJump),
            (152, 159, W_MethodContext.shortConditionalJump),
            (160, 167, W_MethodContext.longUnconditionalJump),
            (168, 171, W_MethodContext.longJumpIfTrue),
            (172, 175, W_MethodContext.longJumpIfFalse),
            (176, W_MethodContext.bytecodePrimAdd),
            (177, W_MethodContext.bytecodePrimSubtract),
            (178, W_MethodContext.bytecodePrimLessThan),
            (179, W_MethodContext.bytecodePrimGreaterThan),
            (180, W_MethodContext.bytecodePrimLessOrEqual),
            (181, W_MethodContext.bytecodePrimGreaterOrEqual),
            (182, W_MethodContext.bytecodePrimEqual),
            (183, W_MethodContext.bytecodePrimNotEqual),
            (184, W_MethodContext.bytecodePrimMultiply),
            (185, W_MethodContext.bytecodePrimDivide),
            (186, W_MethodContext.bytecodePrimMod),
            (187, W_MethodContext.bytecodePrimMakePoint),
            (188, W_MethodContext.bytecodePrimBitShift),
            (189, W_MethodContext.bytecodePrimDiv),
            (190, W_MethodContext.bytecodePrimBitAnd),
            (191, W_MethodContext.bytecodePrimBitOr),
            (192, W_MethodContext.bytecodePrimAt),
            (193, W_MethodContext.bytecodePrimAtPut),
            (194, W_MethodContext.bytecodePrimSize),
            (195, W_MethodContext.bytecodePrimNext),
            (196, W_MethodContext.bytecodePrimNextPut),
            (197, W_MethodContext.bytecodePrimAtEnd),
            (198, W_MethodContext.bytecodePrimEquivalent),
            (199, W_MethodContext.bytecodePrimClass),
            (200, W_MethodContext.bytecodePrimBlockCopy),
            (201, W_MethodContext.bytecodePrimValue),
            (202, W_MethodContext.bytecodePrimValueWithArg),
            (203, W_MethodContext.bytecodePrimDo),
            (204, W_MethodContext.bytecodePrimNew),
            (205, W_MethodContext.bytecodePrimNewWithArg),
            (206, W_MethodContext.bytecodePrimPointX),
            (207, W_MethodContext.bytecodePrimPointY),
            (208, 255, W_MethodContext.sendLiteralSelectorBytecode),
            ]

def initialize_bytecode_table():
    result = [None] * 256
    for entry in BYTECODE_RANGES:
        if len(entry) == 2:
            positions = [entry[0]]
        else:
            positions = range(entry[0], entry[1]+1)
        for pos in positions:
            result[pos] = entry[-1]
    assert None not in result
    return result

BYTECODE_TABLE = initialize_bytecode_table()
