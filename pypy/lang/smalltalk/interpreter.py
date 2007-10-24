import py
from pypy.lang.smalltalk import model, primitives
from pypy.lang.smalltalk import fakeimage


class MissingBytecode(NotImplementedError):
    """Bytecode not implemented yet."""

class IllegalStoreError(Exception):
    """Illegal Store."""


class W_ContextFrame(model.W_Object):
    def __init__(self, w_class, method, receiver, arguments, sender = None):
        model.W_Object.__init__(self, w_class)
        self.method = method
        self.receiver = receiver
        self.sender = sender
        self.stack = []
        self.temps = arguments + [None] * method.tempsize
        self.pc = 0

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
        self.push(self.receiver.getnamedvar(index))

    def pushTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.gettemp(index))

    def pushLiteralConstantBytecode(self, interp):
        index = self.currentBytecode & 31
        self.push(self.method.literals[index])

    def pushLiteralVariableBytecode(self, interp):
        # this bytecode assumes that literals[index] is an Association
        # which is an object with two named vars, and fetches the second
        # named var (the value).
        index = self.currentBytecode & 31
        association = self.method.literals[index]
        self.push(association.getnamedvar(1))

    def storeAndPopReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.receiver.setnamedvar(index, self.pop())

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
        selector = self.method.literals[self.currentBytecode & 15]
        argcount = ((self.currentBytecode >> 4) & 3) - 1
        self._sendSelfSelector(selector, argcount, interp)
        
    def _sendSelfSelector(self, selector, argcount, interp):
        receiver = self.peek(argcount)
        self._sendSelector(selector, argcount, interp,
                           receiver, receiver.w_class)

    def _sendSuperSelector(self, selector, argcount, interp):
        self._sendSelector(selector, argcount, interp, self.receiver,
                           self.method.w_compiledin.w_superclass)

    def _sendSelector(self, selector, argcount, interp,
                      receiver, receiverclass):
        method = receiverclass.lookup(selector)
        assert method
        if method.primitive:
            func = primitives.prim_table[method.primitive]
            try:
                w_result = func(self)
            except primitives.PrimitiveFailedError:
                pass # ignore this error and fall back to the Smalltalk version
            else:
                # the primitive succeeded
                self.push(w_result)
                return
        arguments = self.stack[len(self.stack)-argcount:]
        interp.activeContext = method.createFrame(receiver, arguments, self)
        self.pop_n(argcount + 1)

    def _return(self, object, interp):
        if self.sender is None:   # for tests, when returning from the top-level context
            raise ReturnFromTopLevel(object)
        self.sender.push(object)
        interp.activeContext = self.sender

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
            self.push(self.receiver.getnamedvar(variableIndex))
        elif variableType == 1:
            self.push(self.gettemp(variableIndex))
        elif variableType == 2:
            self.push(self.method.literals[variableIndex])
        elif variableType == 3:
            association = self.method.literals[variableIndex]
            self.push(association.getnamedvar(1))

    def extendedStoreBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.receiver.setnamedvar(variableIndex, self.top())
        elif variableType == 1:
            self.settemp(variableIndex, self.top())
        elif variableType == 2:
            raise IllegalStoreError
        elif variableType == 3:
            association = self.method.literals[variableIndex]
            association.setnamedvar(1,self.top())

    def extendedStoreAndPopBytecode(self, interp):
        self.extendedStoreBytecode(interp)
        self.pop()

    def getExtendedSelectorArgcount(self):
        descriptor = self.getByte()
        return (self.method.literals[descriptor & 31]), (descriptor >> 5)

    def singleExtendedSendBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSelfSelector(selector, argcount, interp)

    def doubleExtendedDoAnythingBytecode(self, interp):
        second = self.getByte()
        third = self.getByte()
        opType = second >> 5
        if opType == 0:
            # selfsend
            self._sendSelfSelector(self.method.literals[third],
                                   second & 31, interp)
        elif opType == 1:
            # supersend
            self._sendSuperSelector(self.method.literals[third],
                                    second & 31, interp)
        elif opType == 2:
            # pushReceiver
            self.push(self.receiver.getnamedvar(third))
        elif opType == 3:
            # pushLiteralConstant
            self.push(self.method.literals[third])
        elif opType == 4:
            # pushLiteralVariable
            association = self.method.literals[third]
            self.push(association.getnamedvar(1))
        elif opType == 5:
            self.receiver.setnamedvar(third, self.top())
        elif opType == 6:
            self.receiver.setnamedvar(third, self.pop())
        elif opType == 7:
            association = self.method.literals[third]
            association.setnamedvar(1,self.top())

    def singleExtendedSuperBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSuperSelector(selector, argcount, interp)

    def secondExtendedSendBytecode(self, interp):
        descriptor = self.getByte()
        selector = self.method.literals[descriptor & 63]
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
            self.push(primitives.prim_table[primitive](self))
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
        raise MissingBytecode

    def bytecodePrimDivide(self, interp):
        raise MissingBytecode

    def bytecodePrimMod(self, interp):
        raise MissingBytecode

    def bytecodePrimMakePoint(self, interp):
        raise MissingBytecode

    def bytecodePrimBitShift(self, interp):
        raise MissingBytecode

    def bytecodePrimDiv(self, interp):
        raise MissingBytecode

    def bytecodePrimBitAnd(self, interp):
        raise MissingBytecode

    def bytecodePrimBitOr(self, interp):
        raise MissingBytecode

    def bytecodePrimAt(self, interp):
        raise MissingBytecode

    def bytecodePrimAtPut(self, interp):
        raise MissingBytecode

    def bytecodePrimSize(self, interp):
        raise MissingBytecode

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
        raise MissingBytecode

    def bytecodePrimNew(self, interp):
        raise MissingBytecode

    def bytecodePrimNewWithArg(self, interp):
        raise MissingBytecode

    def bytecodePrimPointX(self, interp):
        raise MissingBytecode

    def bytecodePrimPointY(self, interp):
        raise MissingBytecode


class Interpreter:

    TRUE = fakeimage.w_true
    FALSE = fakeimage.w_false
    NIL = fakeimage.w_nil
    MONE = fakeimage.w_mone
    ZERO = fakeimage.w_zero
    ONE = fakeimage.w_one
    TWO = fakeimage.w_two
    
    def __init__(self):
        self.activeContext = None

   
    def interpret(self):
        try:
            while True:
                self.step()
        except ReturnFromTopLevel, e:
            return e.object

    def step(self):
        next = self.activeContext.getNextBytecode()
        bytecodeimpl = BYTECODE_TABLE[next]
        bytecodeimpl(self.activeContext, self)
        
class ReturnFromTopLevel(Exception):
    def __init__(self, object):
        self.object = object

BYTECODE_RANGES = [
            (  0,  15, W_ContextFrame.pushReceiverVariableBytecode),
            ( 16,  31, W_ContextFrame.pushTemporaryVariableBytecode),
            ( 32,  63, W_ContextFrame.pushLiteralConstantBytecode),
            ( 64,  95, W_ContextFrame.pushLiteralVariableBytecode),
            ( 96, 103, W_ContextFrame.storeAndPopReceiverVariableBytecode),
            (104, 111, W_ContextFrame.storeAndPopTemporaryVariableBytecode),
            (112, W_ContextFrame.pushReceiverBytecode),
            (113, W_ContextFrame.pushConstantTrueBytecode),
            (114, W_ContextFrame.pushConstantFalseBytecode),
            (115, W_ContextFrame.pushConstantNilBytecode),
            (116, W_ContextFrame.pushConstantMinusOneBytecode),
            (117, W_ContextFrame.pushConstantZeroBytecode),
            (118, W_ContextFrame.pushConstantOneBytecode),
            (119, W_ContextFrame.pushConstantTwoBytecode),
            (120, W_ContextFrame.returnReceiver),
            (121, W_ContextFrame.returnTrue),
            (122, W_ContextFrame.returnFalse),
            (123, W_ContextFrame.returnNil),
            (124, W_ContextFrame.returnTopFromMethod),
            (125, W_ContextFrame.returnTopFromBlock),
            (126, W_ContextFrame.unknownBytecode),
            (127, W_ContextFrame.unknownBytecode),
            (128, W_ContextFrame.extendedPushBytecode),
            (129, W_ContextFrame.extendedStoreBytecode),
            (130, W_ContextFrame.extendedStoreAndPopBytecode),
            (131, W_ContextFrame.singleExtendedSendBytecode),
            (132, W_ContextFrame.doubleExtendedDoAnythingBytecode),
            (133, W_ContextFrame.singleExtendedSuperBytecode),
            (134, W_ContextFrame.secondExtendedSendBytecode),
            (135, W_ContextFrame.popStackBytecode),
            (136, W_ContextFrame.duplicateTopBytecode),
            (137, W_ContextFrame.pushActiveContextBytecode),
            (138, 143, W_ContextFrame.experimentalBytecode),
            (144, 151, W_ContextFrame.shortUnconditionalJump),
            (152, 159, W_ContextFrame.shortConditionalJump),
            (160, 167, W_ContextFrame.longUnconditionalJump),
            (168, 171, W_ContextFrame.longJumpIfTrue),
            (172, 175, W_ContextFrame.longJumpIfFalse),
            (176, W_ContextFrame.bytecodePrimAdd),
            (177, W_ContextFrame.bytecodePrimSubtract),
            (178, W_ContextFrame.bytecodePrimLessThan),
            (179, W_ContextFrame.bytecodePrimGreaterThan),
            (180, W_ContextFrame.bytecodePrimLessOrEqual),
            (181, W_ContextFrame.bytecodePrimGreaterOrEqual),
            (182, W_ContextFrame.bytecodePrimEqual),
            (183, W_ContextFrame.bytecodePrimNotEqual),
            (184, W_ContextFrame.bytecodePrimMultiply),
            (185, W_ContextFrame.bytecodePrimDivide),
            (186, W_ContextFrame.bytecodePrimMod),
            (187, W_ContextFrame.bytecodePrimMakePoint),
            (188, W_ContextFrame.bytecodePrimBitShift),
            (189, W_ContextFrame.bytecodePrimDiv),
            (190, W_ContextFrame.bytecodePrimBitAnd),
            (191, W_ContextFrame.bytecodePrimBitOr),
            (192, W_ContextFrame.bytecodePrimAt),
            (193, W_ContextFrame.bytecodePrimAtPut),
            (194, W_ContextFrame.bytecodePrimSize),
            (195, W_ContextFrame.bytecodePrimNext),
            (196, W_ContextFrame.bytecodePrimNextPut),
            (197, W_ContextFrame.bytecodePrimAtEnd),
            (198, W_ContextFrame.bytecodePrimEquivalent),
            (199, W_ContextFrame.bytecodePrimClass),
            (200, W_ContextFrame.bytecodePrimBlockCopy),
            (201, W_ContextFrame.bytecodePrimValue),
            (202, W_ContextFrame.bytecodePrimValueWithArg),
            (203, W_ContextFrame.bytecodePrimDo),
            (204, W_ContextFrame.bytecodePrimNew),
            (205, W_ContextFrame.bytecodePrimNewWithArg),
            (206, W_ContextFrame.bytecodePrimPointX),
            (207, W_ContextFrame.bytecodePrimPointY),
            (208, 255, W_ContextFrame.sendLiteralSelectorBytecode),
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
