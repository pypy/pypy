import py
from pypy.lang.smalltalk import model, constants, primitives
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk.model import W_ContextPart
from pypy.lang.smalltalk.conftest import option
from pypy.rlib import objectmodel, unroll


class MissingBytecode(Exception):
    """Bytecode not implemented yet."""
    def __init__(self, bytecodename):
        self.bytecodename = bytecodename
        print "MissingBytecode:", bytecodename     # hack for debugging

class IllegalStoreError(Exception):
    """Illegal Store."""

class Interpreter:

    TRUE = objtable.w_true
    FALSE = objtable.w_false
    NIL = objtable.w_nil
    MONE = objtable.w_mone
    ZERO = objtable.w_zero
    ONE = objtable.w_one
    TWO = objtable.w_two

    _w_last_active_context = None
    
    def __init__(self):
        self.w_active_context = None

    def interpret(self):
        try:
            while True:
                self.step()
        except ReturnFromTopLevel, e:
            return e.object

    def should_trace(self):
        return (not objectmodel.we_are_translated()) and option.bc_trace

    def step(self):
        next = self.w_active_context.getNextBytecode()
        if not objectmodel.we_are_translated():
            bytecodeimpl = BYTECODE_TABLE[next]
            if self.should_trace():
                if self._w_last_active_context != self.w_active_context:
                    cnt = 0
                    p = self.w_active_context
                    while p is not None:
                        cnt += 1
                        p = p.w_sender
                    self._last_indent = "  " * cnt
                    self._w_last_active_context = self.w_active_context
                print "%sStack=%s" % (
                    self._last_indent,
                    repr(self.w_active_context.stack),)
                print "%sBytecode at %d (%d:%s):" % (
                    self._last_indent,
                    self.w_active_context.pc,
                    next, bytecodeimpl.__name__,)
            bytecodeimpl(self.w_active_context, self)
        else:
            for code, bytecodeimpl in unrolling_bytecode_table:
                if code == next:
                    bytecodeimpl(self.w_active_context, self)
                    break

        
class ReturnFromTopLevel(Exception):
    def __init__(self, object):
        self.object = object

# ___________________________________________________________________________
# Bytecode Implementations:
#
# "self" is always a W_ContextPart instance.  

class __extend__(W_ContextPart):
    # push bytecodes
    def pushReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.receiver().fetch(index))

    def pushTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.gettemp(index))

    def pushLiteralConstantBytecode(self, interp):
        index = self.currentBytecode & 31
        self.push(self.w_method().getliteral(index))

    def pushLiteralVariableBytecode(self, interp):
        # this bytecode assumes that literals[index] is an Association
        # which is an object with two named vars, and fetches the second
        # named var (the value).
        index = self.currentBytecode & 31
        association = self.w_method().getliteral(index)
        assert isinstance(association, model.W_PointersObject)
        self.push(association.fetch(constants.ASSOCIATION_VALUE_INDEX))

    def storeAndPopReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.receiver().store(index, self.pop())

    def storeAndPopTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.settemp(index, self.pop())

    # push bytecodes
    def pushReceiverBytecode(self, interp):
        self.push(self.receiver())

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
        selector = self.w_method().getliteralsymbol(self.currentBytecode & 15)
        argcount = ((self.currentBytecode >> 4) & 3) - 1
        self._sendSelfSelector(selector, argcount, interp)

    def _sendSelfSelector(self, selector, argcount, interp):
        receiver = self.peek(argcount)
        self._sendSelector(selector, argcount, interp,
                           receiver, receiver.shadow_of_my_class())             

    def _sendSuperSelector(self, selector, argcount, interp):
        s_compiledin = self.w_method().compiledin().as_class_get_shadow()
        self._sendSelector(selector, argcount, interp, self.receiver(),
                           s_compiledin.s_superclass)

    def _sendSelector(self, selector, argcount, interp,
                      receiver, receiverclassshadow):
        if interp.should_trace():
            print "%sSending selector %s to %s" % (
                interp._last_indent, selector, receiver)
        assert argcount >= 0
        method = receiverclassshadow.lookup(selector)
        # XXX catch MethodNotFound here and send doesNotUnderstand:
        if method.primitive:
            func = primitives.prim_table[method.primitive]
            try:
                # note: argcount does not include rcvr
                w_result = func(interp, argcount)
            except primitives.PrimitiveFailedError:
                if interp.should_trace():
                    print "PRIMITIVE FAILED: %d %s" % (method.primitive, selector,)
                pass # ignore this error and fall back to the Smalltalk version
            else:
                # the primitive succeeded
                assert w_result
                self.push(w_result)
                return
        start = len(self.stack) - argcount
        assert start >= 0  # XXX check in the Blue Book what to do in this case
        arguments = self.stack[start:]
        interp.w_active_context = method.create_frame(receiver, arguments, self) 
        self.pop_n(argcount + 1) 

    def _return(self, object, interp, w_return_to):
        # for tests, when returning from the top-level context
        if w_return_to is None:
            raise ReturnFromTopLevel(object)
        w_return_to.push(object)
        interp.w_active_context = w_return_to

    def returnReceiver(self, interp):
        self._return(self.receiver(), interp, self.w_home.w_sender)

    def returnTrue(self, interp):
        self._return(interp.TRUE, interp, self.w_home.w_sender)

    def returnFalse(self, interp):
        self._return(interp.FALSE, interp, self.w_home.w_sender)

    def returnNil(self, interp):
        self._return(interp.NIL, interp, self.w_home.w_sender)

    def returnTopFromMethod(self, interp):
        self._return(self.top(), interp, self.w_home.w_sender)

    def returnTopFromBlock(self, interp):
        self._return(self.top(), interp, self.w_sender)

    def unknownBytecode(self, interp):
        raise MissingBytecode("unknownBytecode")

    def extendedVariableTypeAndIndex(self):
        descriptor = self.getByte()
        return ((descriptor >> 6) & 3), (descriptor & 63)

    def extendedPushBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.push(self.receiver().fetch(variableIndex))
        elif variableType == 1:
            self.push(self.gettemp(variableIndex))
        elif variableType == 2:
            self.push(self.w_method().getliteral(variableIndex))
        elif variableType == 3:
            association = self.w_method().getliteral(variableIndex)
            assert isinstance(association, model.W_PointersObject)
            self.push(association.fetch(constants.ASSOCIATION_VALUE_INDEX))

    def extendedStoreBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.receiver().store(variableIndex, self.top())
        elif variableType == 1:
            self.settemp(variableIndex, self.top())
        elif variableType == 2:
            raise IllegalStoreError
        elif variableType == 3:
            association = self.w_method().getliteral(variableIndex)
            assert isinstance(association, model.W_PointersObject)
            association.store(constants.ASSOCIATION_VALUE_INDEX, self.top())

    def extendedStoreAndPopBytecode(self, interp):
        self.extendedStoreBytecode(interp)
        self.pop()

    def getExtendedSelectorArgcount(self):
        descriptor = self.getByte()
        return ((self.w_method().getliteralsymbol(descriptor & 31)),
                (descriptor >> 5))

    def singleExtendedSendBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSelfSelector(selector, argcount, interp)

    def doubleExtendedDoAnythingBytecode(self, interp):
        second = self.getByte()
        third = self.getByte()
        opType = second >> 5
        if opType == 0:
            # selfsend
            self._sendSelfSelector(self.w_method().getliteralsymbol(third),
                                   second & 31, interp)
        elif opType == 1:
            # supersend
            self._sendSuperSelector(self.w_method().getliteralsymbol(third),
                                    second & 31, interp)
        elif opType == 2:
            # pushReceiver
            self.push(self.receiver().fetch(third))
        elif opType == 3:
            # pushLiteralConstant
            self.push(self.w_method().getliteral(third))
        elif opType == 4:
            # pushLiteralVariable
            association = self.w_method().getliteral(third)
            assert isinstance(association, model.W_PointersObject)
            self.push(association.fetch(constants.ASSOCIATION_VALUE_INDEX))
        elif opType == 5:
            self.receiver().store(third, self.top())
        elif opType == 6:
            self.receiver().store(third, self.pop())
        elif opType == 7:
            association = self.w_method().getliteral(third)
            assert isinstance(association, model.W_PointersObject)
            association.store(constants.ASSOCIATION_VALUE_INDEX, self.top())

    def singleExtendedSuperBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSuperSelector(selector, argcount, interp)

    def secondExtendedSendBytecode(self, interp):
        descriptor = self.getByte()
        selector = self.w_method().getliteralsymbol(descriptor & 63)
        argcount = descriptor >> 6
        self._sendSelfSelector(selector, argcount, interp)

    def popStackBytecode(self, interp):
        self.pop()

    def experimentalBytecode(self, interp):
        raise MissingBytecode("experimentalBytecode")

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
        self.jump((((self.currentBytecode & 7) - 4) << 8) + self.getByte())

    def longJumpPosition(self):
        return ((self.currentBytecode & 3) << 8) + self.getByte()

    def longJumpIfTrue(self, interp):
        self.jumpConditional(interp.TRUE,self.longJumpPosition())

    def longJumpIfFalse(self, interp):
        self.jumpConditional(interp.FALSE,self.longJumpPosition())

    def callPrimitiveAndPush(self, primitive, selector,
                             argcount, interp):
        #XXX do something clever later
        try:
            # note that argcount does not include self
            self.push(primitives.prim_table[primitive](interp, argcount))
        except primitives.PrimitiveFailedError:
            self._sendSelfSelector(selector, argcount, interp)
        #self._sendSelfSelector(selector, argcount, interp)

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
        self.callPrimitiveAndPush(primitives.MOD, "\\\\", 1, interp)

    def bytecodePrimMakePoint(self, interp):
        raise MissingBytecode("bytecodePrimMakePoint")

    def bytecodePrimBitShift(self, interp):
        self.callPrimitiveAndPush(primitives.BIT_SHIFT, "bitShift:", 1, interp)

    def bytecodePrimDiv(self, interp):
        self.callPrimitiveAndPush(primitives.DIV, "//", 1, interp)

    def bytecodePrimBitAnd(self, interp):
        self.callPrimitiveAndPush(primitives.BIT_AND, "bitAnd:", 1, interp)

    def bytecodePrimBitOr(self, interp):
        self.callPrimitiveAndPush(primitives.BIT_OR, "bitOr:", 1, interp)

    def bytecodePrimAt(self, interp):
        # n.b.: depending on the type of the receiver, this may invoke
        # primitives.AT, primitives.STRING_AT, or something else for all
        # I know.  
        #self.callPrimitiveAndPush(primitives.AT, "at:", 1, interp)
        self._sendSelfSelector("at:", 1, interp)

    def bytecodePrimAtPut(self, interp):
        # n.b. as above
        #self.callPrimitiveAndPush(primitives.AT_PUT, "at:put:", 2, interp)
        self._sendSelfSelector("at:put:", 2, interp)

    def bytecodePrimSize(self, interp):
        self.callPrimitiveAndPush(primitives.SIZE, "size", 0, interp)

    def bytecodePrimNext(self, interp):
        self.callPrimitiveAndPush(primitives.NEXT, "next", 0, interp)

    def bytecodePrimNextPut(self, interp):
        self.callPrimitiveAndPush(primitives.NEXT_PUT, "nextPut:", 1, interp)

    def bytecodePrimAtEnd(self, interp):
        self.callPrimitiveAndPush(primitives.AT_END, "atEnd", 0, interp)

    def bytecodePrimEquivalent(self, interp):
        self.callPrimitiveAndPush(primitives.EQUIVALENT, "==", 1, interp)

    def bytecodePrimClass(self, interp):
        self.callPrimitiveAndPush(
            primitives.CLASS, "class", 0, interp)

    def bytecodePrimBlockCopy(self, interp):
        self.callPrimitiveAndPush(
            primitives.PRIMITIVE_BLOCK_COPY, "blockCopy:", 1, interp)

    def bytecodePrimValue(self, interp):
        self.callPrimitiveAndPush(
            primitives.PRIMITIVE_VALUE, "value", 0, interp)

    def bytecodePrimValueWithArg(self, interp):
        self.callPrimitiveAndPush(
            primitives.PRIMITIVE_VALUE, "value:", 1, interp)

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


BYTECODE_RANGES = [
            (  0,  15, W_ContextPart.pushReceiverVariableBytecode),
            ( 16,  31, W_ContextPart.pushTemporaryVariableBytecode),
            ( 32,  63, W_ContextPart.pushLiteralConstantBytecode),
            ( 64,  95, W_ContextPart.pushLiteralVariableBytecode),
            ( 96, 103, W_ContextPart.storeAndPopReceiverVariableBytecode),
            (104, 111, W_ContextPart.storeAndPopTemporaryVariableBytecode),
            (112, W_ContextPart.pushReceiverBytecode),
            (113, W_ContextPart.pushConstantTrueBytecode),
            (114, W_ContextPart.pushConstantFalseBytecode),
            (115, W_ContextPart.pushConstantNilBytecode),
            (116, W_ContextPart.pushConstantMinusOneBytecode),
            (117, W_ContextPart.pushConstantZeroBytecode),
            (118, W_ContextPart.pushConstantOneBytecode),
            (119, W_ContextPart.pushConstantTwoBytecode),
            (120, W_ContextPart.returnReceiver),
            (121, W_ContextPart.returnTrue),
            (122, W_ContextPart.returnFalse),
            (123, W_ContextPart.returnNil),
            (124, W_ContextPart.returnTopFromMethod),
            (125, W_ContextPart.returnTopFromBlock),
            (126, W_ContextPart.unknownBytecode),
            (127, W_ContextPart.unknownBytecode),
            (128, W_ContextPart.extendedPushBytecode),
            (129, W_ContextPart.extendedStoreBytecode),
            (130, W_ContextPart.extendedStoreAndPopBytecode),
            (131, W_ContextPart.singleExtendedSendBytecode),
            (132, W_ContextPart.doubleExtendedDoAnythingBytecode),
            (133, W_ContextPart.singleExtendedSuperBytecode),
            (134, W_ContextPart.secondExtendedSendBytecode),
            (135, W_ContextPart.popStackBytecode),
            (136, W_ContextPart.duplicateTopBytecode),
            (137, W_ContextPart.pushActiveContextBytecode),
            (138, 143, W_ContextPart.experimentalBytecode),
            (144, 151, W_ContextPart.shortUnconditionalJump),
            (152, 159, W_ContextPart.shortConditionalJump),
            (160, 167, W_ContextPart.longUnconditionalJump),
            (168, 171, W_ContextPart.longJumpIfTrue),
            (172, 175, W_ContextPart.longJumpIfFalse),
            (176, W_ContextPart.bytecodePrimAdd),
            (177, W_ContextPart.bytecodePrimSubtract),
            (178, W_ContextPart.bytecodePrimLessThan),
            (179, W_ContextPart.bytecodePrimGreaterThan),
            (180, W_ContextPart.bytecodePrimLessOrEqual),
            (181, W_ContextPart.bytecodePrimGreaterOrEqual),
            (182, W_ContextPart.bytecodePrimEqual),
            (183, W_ContextPart.bytecodePrimNotEqual),
            (184, W_ContextPart.bytecodePrimMultiply),
            (185, W_ContextPart.bytecodePrimDivide),
            (186, W_ContextPart.bytecodePrimMod),
            (187, W_ContextPart.bytecodePrimMakePoint),
            (188, W_ContextPart.bytecodePrimBitShift),
            (189, W_ContextPart.bytecodePrimDiv),
            (190, W_ContextPart.bytecodePrimBitAnd),
            (191, W_ContextPart.bytecodePrimBitOr),
            (192, W_ContextPart.bytecodePrimAt),
            (193, W_ContextPart.bytecodePrimAtPut),
            (194, W_ContextPart.bytecodePrimSize),
            (195, W_ContextPart.bytecodePrimNext),
            (196, W_ContextPart.bytecodePrimNextPut),
            (197, W_ContextPart.bytecodePrimAtEnd),
            (198, W_ContextPart.bytecodePrimEquivalent),
            (199, W_ContextPart.bytecodePrimClass),
            (200, W_ContextPart.bytecodePrimBlockCopy),
            (201, W_ContextPart.bytecodePrimValue),
            (202, W_ContextPart.bytecodePrimValueWithArg),
            (203, W_ContextPart.bytecodePrimDo),
            (204, W_ContextPart.bytecodePrimNew),
            (205, W_ContextPart.bytecodePrimNewWithArg),
            (206, W_ContextPart.bytecodePrimPointX),
            (207, W_ContextPart.bytecodePrimPointY),
            (208, 255, W_ContextPart.sendLiteralSelectorBytecode),
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
unrolling_bytecode_table = unroll.unrolling_iterable(enumerate(BYTECODE_TABLE))
