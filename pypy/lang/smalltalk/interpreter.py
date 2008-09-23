import py
from pypy.lang.smalltalk.shadow import ContextPartShadow, MethodContextShadow, BlockContextShadow
from pypy.lang.smalltalk import model, constants, primitives
from pypy.lang.smalltalk.shadow import ContextPartShadow
from pypy.lang.smalltalk.conftest import option
from pypy.rlib import objectmodel, unroll
from pypy.lang.smalltalk import wrapper


class MissingBytecode(Exception):
    """Bytecode not implemented yet."""
    def __init__(self, bytecodename):
        self.bytecodename = bytecodename
        print "MissingBytecode:", bytecodename     # hack for debugging

class IllegalStoreError(Exception):
    """Illegal Store."""

class Interpreter(object):

    _w_last_active_context = None
    
    def __init__(self, space):
        self._w_active_context = None
        self.space = space
        self.cnt = 0

    def w_active_context(self):
        return self._w_active_context

    def store_w_active_context(self, w_context):
        assert isinstance(w_context, model.W_PointersObject)
        self._w_active_context = w_context

    def s_active_context(self):
        return self.w_active_context().as_context_get_shadow(self.space)

    def interpret(self):
        try:
            while True:
                self.step()
        except ReturnFromTopLevel, e:
            return e.object

    def should_trace(self):
        return (not objectmodel.we_are_translated()) and option.bc_trace

    def step(self):
        next = self.s_active_context().getNextBytecode()
        # we_are_translated returns false on top of CPython and true when
        # translating the interpreter
        if not objectmodel.we_are_translated():
            bytecodeimpl = BYTECODE_TABLE[next]

            if self.should_trace():
                if self._w_last_active_context != self.w_active_context():
                    cnt = 0
                    p = self.w_active_context()
                    # AK make method
                    while p is not self.space.w_nil:
                        cnt += 1
                                                  # Do not update the context
                                                  # for this action.
                        p = p.as_context_get_shadow(self.space).w_sender()
                    self._last_indent = "  " * cnt
                    self._w_last_active_context = self.w_active_context()

                print "%sStack=%s" % (
                    self._last_indent,
                    repr(self.s_active_context().stack()),)
                print "%sBytecode at %d (%d:%s):" % (
                    self._last_indent,
                    self.s_active_context().pc(),
                    next, bytecodeimpl.__name__,)

            bytecodeimpl(self.s_active_context(), self)

        else:
            # this is a performance optimization: when translating the
            # interpreter, the bytecode dispatching is not implemented as a
            # list lookup and an indirect call but as a switch. The for loop
            # below produces the switch (by being unrolled).
            for code, bytecodeimpl in unrolling_bytecode_table:
                if code == next:
                    bytecodeimpl(self.s_active_context(), self)
                    break

        
class ReturnFromTopLevel(Exception):
    def __init__(self, object):
        self.object = object

# ___________________________________________________________________________
# Bytecode Implementations:
#
# "self" is always a ContextPartShadow instance.  

# __extend__ adds new methods to the ContextPartShadow class
class __extend__(ContextPartShadow):
    # push bytecodes
    def pushReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 15
        self.push(self.w_receiver().fetch(self.space, index))

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
        w_association = self.w_method().getliteral(index)
        association = wrapper.AssociationWrapper(self.space, w_association)
        self.push(association.value())

    def storeAndPopReceiverVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.w_receiver().store(self.space, index, self.pop())

    def storeAndPopTemporaryVariableBytecode(self, interp):
        index = self.currentBytecode & 7
        self.settemp(index, self.pop())

    # push bytecodes
    def pushReceiverBytecode(self, interp):
        self.push(self.w_receiver())

    def pushConstantTrueBytecode(self, interp):
        self.push(interp.space.w_true)

    def pushConstantFalseBytecode(self, interp):
        self.push(interp.space.w_false)

    def pushConstantNilBytecode(self, interp):
        self.push(interp.space.w_nil)

    def pushConstantMinusOneBytecode(self, interp):
        self.push(interp.space.w_minus_one)

    def pushConstantZeroBytecode(self, interp):
        self.push(interp.space.w_zero)

    def pushConstantOneBytecode(self, interp):
        self.push(interp.space.w_one)

    def pushConstantTwoBytecode(self, interp):
        self.push(interp.space.w_two)

    def pushActiveContextBytecode(self, interp):
        self.push(self.w_self())

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
                           receiver, receiver.shadow_of_my_class(self.space))

    def _sendSuperSelector(self, selector, argcount, interp):
        w_compiledin = self.w_method().compiledin()
        assert isinstance(w_compiledin, model.W_PointersObject)
        s_compiledin = w_compiledin.as_class_get_shadow(self.space)
        self._sendSelector(selector, argcount, interp, self.w_receiver(),
                           s_compiledin.s_superclass())

    def _sendSelector(self, selector, argcount, interp,
                      receiver, receiverclassshadow):
        if interp.should_trace():
            print "%sSending selector %r to %r with: %r" % (
                interp._last_indent, selector, receiver,
                [self.peek(argcount-1-i) for i in range(argcount)])
            pass
        assert argcount >= 0
        method = receiverclassshadow.lookup(selector)
        # XXX catch MethodNotFound here and send doesNotUnderstand:
        # AK shouln't that be done in lookup itself, please check what spec says about DNU in case of super sends.
        if method.primitive:
            # the primitive pushes the result (if any) onto the stack itself
            code = method.primitive
            if interp.should_trace():
                print "%sActually calling primitive %d" % (interp._last_indent, code,)
            if objectmodel.we_are_translated():
                for i, func in primitives.unrolling_prim_table:
                    if i == code:
                        try:
                            func(interp, argcount)
                            return
                        except primitives.PrimitiveFailedError:
                            break
            else:
                func = primitives.prim_table[code]
                try:
                    # note: argcount does not include rcvr
                    w_result = func(interp, argcount)
                    return
                except primitives.PrimitiveFailedError:
                    if interp.should_trace():
                        print "PRIMITIVE FAILED: %d %s" % (method.primitive, selector,)
                    pass # ignore this error and fall back to the Smalltalk version
        arguments = self.pop_and_return_n(argcount)
        frame = method.create_frame(self.space, receiver, arguments,
                                    self.w_self())
        interp.store_w_active_context(frame)
        self.pop()

    def _return(self, object, interp, w_return_to):
        # for tests, when returning from the top-level context
        if w_return_to is self.space.w_nil:
            raise ReturnFromTopLevel(object)
        w_return_to.as_context_get_shadow(self.space).push(object)
        interp.store_w_active_context(w_return_to)

    def returnReceiver(self, interp):
        self._return(self.w_receiver(), interp, self.s_home().w_sender())

    def returnTrue(self, interp):
        self._return(interp.space.w_true, interp, self.s_home().w_sender())

    def returnFalse(self, interp):
        self._return(interp.space.w_false, interp, self.s_home().w_sender())

    def returnNil(self, interp):
        self._return(interp.space.w_nil, interp, self.s_home().w_sender())

    def returnTopFromMethod(self, interp):
        self._return(self.top(), interp, self.s_home().w_sender())

    def returnTopFromBlock(self, interp):
        self._return(self.top(), interp, self.w_sender())

    def unknownBytecode(self, interp):
        raise MissingBytecode("unknownBytecode")

    def extendedVariableTypeAndIndex(self):
        # AK please explain this method (a helper, I guess)
        descriptor = self.getbytecode()
        return ((descriptor >> 6) & 3), (descriptor & 63)

    def extendedPushBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.push(self.w_receiver().fetch(self.space, variableIndex))
        elif variableType == 1:
            self.push(self.gettemp(variableIndex))
        elif variableType == 2:
            self.push(self.w_method().getliteral(variableIndex))
        elif variableType == 3:
            w_association = self.w_method().getliteral(variableIndex)
            association = wrapper.AssociationWrapper(self.space, w_association)
            self.push(association.value())
        else:
            assert 0
        
    def extendedStoreBytecode(self, interp):
        variableType, variableIndex = self.extendedVariableTypeAndIndex()
        if variableType == 0:
            self.w_receiver().store(self.space, variableIndex, self.top())
        elif variableType == 1:
            self.settemp(variableIndex, self.top())
        elif variableType == 2:
            raise IllegalStoreError
        elif variableType == 3:
            w_association = self.w_method().getliteral(variableIndex)
            association = wrapper.AssociationWrapper(self.space, w_association)
            association.store_value(self.top())

    def extendedStoreAndPopBytecode(self, interp):
        self.extendedStoreBytecode(interp)
        self.pop()

    def getExtendedSelectorArgcount(self):
        descriptor = self.getbytecode()
        return ((self.w_method().getliteralsymbol(descriptor & 31)),
                (descriptor >> 5))

    def singleExtendedSendBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSelfSelector(selector, argcount, interp)

    def doubleExtendedDoAnythingBytecode(self, interp):
        second = self.getbytecode()
        third = self.getbytecode()
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
            self.push(self.w_receiver().fetch(self.space, third))
        elif opType == 3:
            # pushLiteralConstant
            self.push(self.w_method().getliteral(third))
        elif opType == 4:
            # pushLiteralVariable
            w_association = self.w_method().getliteral(third)
            association = wrapper.AssociationWrapper(self.space, w_association)
            self.push(association.value())
        elif opType == 5:
            self.w_receiver().store(self.space, third, self.top())
        elif opType == 6:
            self.w_receiver().store(self.space, third, self.pop())
        elif opType == 7:
            w_association = self.w_method().getliteral(third)
            association = wrapper.AssociationWrapper(self.space, w_association)
            association.store_value(self.top())

    def singleExtendedSuperBytecode(self, interp):
        selector, argcount = self.getExtendedSelectorArgcount()
        self._sendSuperSelector(selector, argcount, interp)

    def secondExtendedSendBytecode(self, interp):
        descriptor = self.getbytecode()
        selector = self.w_method().getliteralsymbol(descriptor & 63)
        argcount = descriptor >> 6
        self._sendSelfSelector(selector, argcount, interp)

    def popStackBytecode(self, interp):
        self.pop()

    def experimentalBytecode(self, interp):
        raise MissingBytecode("experimentalBytecode")

    def jump(self,offset):
        self.store_pc(self.pc() + offset)

    def jumpConditional(self,bool,position):
        if self.top() == bool:
            self.jump(position)
        self.pop()

    def shortJumpPosition(self):
        return (self.currentBytecode & 7) + 1

    def shortUnconditionalJump(self, interp):
        self.jump(self.shortJumpPosition())

    def shortConditionalJump(self, interp):
        self.jumpConditional(interp.space.w_false, self.shortJumpPosition())

    def longUnconditionalJump(self, interp):
        self.jump((((self.currentBytecode & 7) - 4) << 8) + self.getbytecode())

    def longJumpPosition(self):
        return ((self.currentBytecode & 3) << 8) + self.getbytecode()

    def longJumpIfTrue(self, interp):
        self.jumpConditional(interp.space.w_true, self.longJumpPosition())

    def longJumpIfFalse(self, interp):
        self.jumpConditional(interp.space.w_false, self.longJumpPosition())

    # RPython trick: specialize the following function on its second argument
    # this makes sure that the primitive call is a direct one
    @objectmodel.specialize.arg(1)
    def callPrimitive(self, primitive, selector, argcount, interp):
        # WARNING: this is used for bytecodes for which it is safe to
        # directly call the primitive.  In general, it is not safe: for
        # example, depending on the type of the receiver, bytecodePrimAt
        # may invoke primitives.AT, primitives.STRING_AT, or anything
        # else that the user put in a class in an 'at:' method.
        # The rule of thumb is that primitives with only int and float
        # in their unwrap_spec are safe.
        for i, func in primitives.unrolling_prim_table:
            if i == primitive:
                try:
                    func(interp, argcount)
                    return
                except primitives.PrimitiveFailedError:
                    break
        self._sendSelfSelector(selector, argcount, interp)

    def callPrimitive2(self, primitive1, primitive2,
                       selector, argcount, interp):
        # same as callPrimitive(), but tries two primitives before falling
        # back to the general case.
        try:
            primitives.prim_table[primitive1](interp, argcount)
            # the primitive pushes the result (if any) onto the stack itself
        except primitives.PrimitiveFailedError:
            self.callPrimitive(primitive2, selector, argcount, interp)

    def bytecodePrimAdd(self, interp):
        self.callPrimitive(primitives.ADD,
                           "+", 1, interp)

    def bytecodePrimSubtract(self, interp):
        self.callPrimitive(primitives.SUBTRACT,
                           "-", 1, interp)

    def bytecodePrimLessThan(self, interp):        
        self.callPrimitive(primitives.LESSTHAN,
                           "<", 1, interp)

    def bytecodePrimGreaterThan(self, interp):
        self.callPrimitive(primitives.GREATERTHAN,
                          ">", 1, interp)

    def bytecodePrimLessOrEqual(self, interp):
        self.callPrimitive(primitives.LESSOREQUAL,
                           "<=", 1, interp)

    def bytecodePrimGreaterOrEqual(self, interp):
        self.callPrimitive(primitives.GREATEROREQUAL,
                           ">=", 1, interp)

    def bytecodePrimEqual(self, interp):
        self.callPrimitive(primitives.EQUAL,
                            "=", 1, interp)

    def bytecodePrimNotEqual(self, interp):
        self.callPrimitive(primitives.NOTEQUAL,
                           "~=", 1, interp)

    def bytecodePrimMultiply(self, interp):
        self.callPrimitive(primitives.MULTIPLY,
                           "*", 1, interp)

    def bytecodePrimDivide(self, interp):
        self.callPrimitive(primitives.DIVIDE,
                           "/", 1, interp)

    def bytecodePrimMod(self, interp):
        self.callPrimitive(primitives.MOD, "\\\\", 1, interp)

    def bytecodePrimMakePoint(self, interp):
        self.callPrimitive(primitives.MAKE_POINT, "@", 1, interp)

    def bytecodePrimBitShift(self, interp):
        self.callPrimitive(primitives.BIT_SHIFT, "bitShift:", 1, interp)

    def bytecodePrimDiv(self, interp):
        self.callPrimitive(primitives.DIV, "//", 1, interp)

    def bytecodePrimBitAnd(self, interp):
        self.callPrimitive(primitives.BIT_AND, "bitAnd:", 1, interp)

    def bytecodePrimBitOr(self, interp):
        self.callPrimitive(primitives.BIT_OR, "bitOr:", 1, interp)

    def bytecodePrimAt(self, interp):
        # n.b.: depending on the type of the receiver, this may invoke
        # primitives.AT, primitives.STRING_AT, or something else for all
        # I know.  
        self._sendSelfSelector("at:", 1, interp)

    def bytecodePrimAtPut(self, interp):
        # n.b. as above
        self._sendSelfSelector("at:put:", 2, interp)

    def bytecodePrimSize(self, interp):
        self._sendSelfSelector("size", 0, interp)

    def bytecodePrimNext(self, interp):
        self._sendSelfSelector("next", 0, interp)

    def bytecodePrimNextPut(self, interp):
        self._sendSelfSelector("nextPut:", 1, interp)

    def bytecodePrimAtEnd(self, interp):
        self._sendSelfSelector("atEnd", 0, interp)

    def bytecodePrimEquivalent(self, interp):
        # short-circuit: classes cannot override the '==' method,
        # which cannot fail
        primitives.prim_table[primitives.EQUIVALENT](interp, 1)

    def bytecodePrimClass(self, interp):
        # short-circuit: classes cannot override the 'class' method,
        # which cannot fail
        primitives.prim_table[primitives.CLASS](interp, 0)

    def bytecodePrimBlockCopy(self, interp):
        # the primitive checks the class of the receiver
        self.callPrimitive(primitives.PRIMITIVE_BLOCK_COPY,
                           "blockCopy:", 1, interp)

    def bytecodePrimValue(self, interp):
        # the primitive checks the class of the receiver
        self.callPrimitive(
            primitives.PRIMITIVE_VALUE, "value", 0, interp)

    def bytecodePrimValueWithArg(self, interp):
        # the primitive checks the class of the receiver
        # Note that the PRIMITIVE_VALUE_WITH_ARGS takes an array of
        # arguments but this bytecode is about the one-argument case.
        # The PRIMITIVE_VALUE is general enough to take any number of
        # arguments from the stack, so it's the one we need to use here.
        self.callPrimitive(
            primitives.PRIMITIVE_VALUE, "value:", 1, interp)

    def bytecodePrimDo(self, interp):
        self._sendSelfSelector("do:", 1, interp)

    def bytecodePrimNew(self, interp):
        self._sendSelfSelector("new", 0, interp)

    def bytecodePrimNewWithArg(self, interp):
        self._sendSelfSelector("new:", 1, interp)

    def bytecodePrimPointX(self, interp):
        self._sendSelfSelector("x", 0, interp)

    def bytecodePrimPointY(self, interp):
        self._sendSelfSelector("y", 0, interp)


BYTECODE_RANGES = [
            (  0,  15, ContextPartShadow.pushReceiverVariableBytecode),
            ( 16,  31, ContextPartShadow.pushTemporaryVariableBytecode),
            ( 32,  63, ContextPartShadow.pushLiteralConstantBytecode),
            ( 64,  95, ContextPartShadow.pushLiteralVariableBytecode),
            ( 96, 103, ContextPartShadow.storeAndPopReceiverVariableBytecode),
            (104, 111, ContextPartShadow.storeAndPopTemporaryVariableBytecode),
            (112, ContextPartShadow.pushReceiverBytecode),
            (113, ContextPartShadow.pushConstantTrueBytecode),
            (114, ContextPartShadow.pushConstantFalseBytecode),
            (115, ContextPartShadow.pushConstantNilBytecode),
            (116, ContextPartShadow.pushConstantMinusOneBytecode),
            (117, ContextPartShadow.pushConstantZeroBytecode),
            (118, ContextPartShadow.pushConstantOneBytecode),
            (119, ContextPartShadow.pushConstantTwoBytecode),
            (120, ContextPartShadow.returnReceiver),
            (121, ContextPartShadow.returnTrue),
            (122, ContextPartShadow.returnFalse),
            (123, ContextPartShadow.returnNil),
            (124, ContextPartShadow.returnTopFromMethod),
            (125, ContextPartShadow.returnTopFromBlock),
            (126, ContextPartShadow.unknownBytecode),
            (127, ContextPartShadow.unknownBytecode),
            (128, ContextPartShadow.extendedPushBytecode),
            (129, ContextPartShadow.extendedStoreBytecode),
            (130, ContextPartShadow.extendedStoreAndPopBytecode),
            (131, ContextPartShadow.singleExtendedSendBytecode),
            (132, ContextPartShadow.doubleExtendedDoAnythingBytecode),
            (133, ContextPartShadow.singleExtendedSuperBytecode),
            (134, ContextPartShadow.secondExtendedSendBytecode),
            (135, ContextPartShadow.popStackBytecode),
            (136, ContextPartShadow.duplicateTopBytecode),
            (137, ContextPartShadow.pushActiveContextBytecode),
            (138, 143, ContextPartShadow.experimentalBytecode),
            (144, 151, ContextPartShadow.shortUnconditionalJump),
            (152, 159, ContextPartShadow.shortConditionalJump),
            (160, 167, ContextPartShadow.longUnconditionalJump),
            (168, 171, ContextPartShadow.longJumpIfTrue),
            (172, 175, ContextPartShadow.longJumpIfFalse),
            (176, ContextPartShadow.bytecodePrimAdd),
            (177, ContextPartShadow.bytecodePrimSubtract),
            (178, ContextPartShadow.bytecodePrimLessThan),
            (179, ContextPartShadow.bytecodePrimGreaterThan),
            (180, ContextPartShadow.bytecodePrimLessOrEqual),
            (181, ContextPartShadow.bytecodePrimGreaterOrEqual),
            (182, ContextPartShadow.bytecodePrimEqual),
            (183, ContextPartShadow.bytecodePrimNotEqual),
            (184, ContextPartShadow.bytecodePrimMultiply),
            (185, ContextPartShadow.bytecodePrimDivide),
            (186, ContextPartShadow.bytecodePrimMod),
            (187, ContextPartShadow.bytecodePrimMakePoint),
            (188, ContextPartShadow.bytecodePrimBitShift),
            (189, ContextPartShadow.bytecodePrimDiv),
            (190, ContextPartShadow.bytecodePrimBitAnd),
            (191, ContextPartShadow.bytecodePrimBitOr),
            (192, ContextPartShadow.bytecodePrimAt),
            (193, ContextPartShadow.bytecodePrimAtPut),
            (194, ContextPartShadow.bytecodePrimSize),
            (195, ContextPartShadow.bytecodePrimNext),
            (196, ContextPartShadow.bytecodePrimNextPut),
            (197, ContextPartShadow.bytecodePrimAtEnd),
            (198, ContextPartShadow.bytecodePrimEquivalent),
            (199, ContextPartShadow.bytecodePrimClass),
            (200, ContextPartShadow.bytecodePrimBlockCopy),
            (201, ContextPartShadow.bytecodePrimValue),
            (202, ContextPartShadow.bytecodePrimValueWithArg),
            (203, ContextPartShadow.bytecodePrimDo),
            (204, ContextPartShadow.bytecodePrimNew),
            (205, ContextPartShadow.bytecodePrimNewWithArg),
            (206, ContextPartShadow.bytecodePrimPointX),
            (207, ContextPartShadow.bytecodePrimPointY),
            (208, 255, ContextPartShadow.sendLiteralSelectorBytecode),
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
