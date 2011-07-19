"""StdObjSpace custom opcode implementations"""

import operator

from pypy.rlib.unroll import unrolling_iterable
from pypy.interpreter import pyopcode, function
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.module.__builtin__ import Module
from pypy.objspace.std import intobject, smallintobject
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.listobject import W_ListObject


class BaseFrame(PyFrame):
    """These opcodes are always overridden."""

    def LIST_APPEND(f, oparg, next_instr):
        w = f.popvalue()
        v = f.peekvalue(oparg - 1)
        if type(v) is W_ListObject:
            v.append(w)
        else:
            raise AssertionError


def small_int_BINARY_ADD(f, oparg, next_instr):
    w_2 = f.popvalue()
    w_1 = f.popvalue()
    if (type(w_1) is smallintobject.W_SmallIntObject and
        type(w_2) is smallintobject.W_SmallIntObject):
        try:
            w_result = smallintobject.add__SmallInt_SmallInt(f.space, w_1, w_2)
        except FailedToImplement:
            w_result = f.space.add(w_1, w_2)
    else:
        w_result = f.space.add(w_1, w_2)
    f.pushvalue(w_result)


def int_BINARY_ADD(f, oparg, next_instr):
    w_2 = f.popvalue()
    w_1 = f.popvalue()
    if (type(w_1) is intobject.W_IntObject and
        type(w_2) is intobject.W_IntObject):
        try:
            w_result = intobject.add__Int_Int(f.space, w_1, w_2)
        except FailedToImplement:
            w_result = f.space.add(w_1, w_2)
    else:
        w_result = f.space.add(w_1, w_2)
    f.pushvalue(w_result)


def list_BINARY_SUBSCR(f, oparg, next_instr):
    w_2 = f.popvalue()
    w_1 = f.popvalue()
    if type(w_1) is W_ListObject and type(w_2) is intobject.W_IntObject:
        try:
            w_result = w_1.wrappeditems[w_2.intval]
        except IndexError:
            raise OperationError(f.space.w_IndexError,
                f.space.wrap("list index out of range"))
    else:
        w_result = f.space.getitem(w_1, w_2)
    f.pushvalue(w_result)

compare_table = [
    "lt",   # "<"
    "le",   # "<="
    "eq",   # "=="
    "ne",   # "!="
    "gt",   # ">"
    "ge",   # ">="
    ]
unrolling_compare_ops = unrolling_iterable(enumerate(compare_table))

def fast_COMPARE_OP(f, testnum, next_instr):
    w_2 = f.popvalue()
    w_1 = f.popvalue()
    w_result = None
    if (type(w_2) is intobject.W_IntObject and
        type(w_1) is intobject.W_IntObject and
        testnum < len(compare_table)):
        for i, attr in unrolling_compare_ops:
            if i == testnum:
                op = getattr(operator, attr)
                w_result = f.space.newbool(op(w_1.intval,
                                              w_2.intval))
                break
    else:
        for i, attr in pyopcode.unrolling_compare_dispatch_table:
            if i == testnum:
                w_result = getattr(f, attr)(w_1, w_2)
                break
        else:
            raise pyopcode.BytecodeCorruption, "bad COMPARE_OP oparg"
    f.pushvalue(w_result)


def build_frame(space):
    """Consider the objspace config and return a patched frame object."""
    class StdObjSpaceFrame(BaseFrame):
        pass
    if space.config.objspace.std.optimized_int_add:
        if space.config.objspace.std.withsmallint:
            StdObjSpaceFrame.BINARY_ADD = small_int_BINARY_ADD
        else:
            StdObjSpaceFrame.BINARY_ADD = int_BINARY_ADD
    if space.config.objspace.std.optimized_list_getitem:
        StdObjSpaceFrame.BINARY_SUBSCR = list_BINARY_SUBSCR
    if space.config.objspace.opcodes.CALL_METHOD:
        from pypy.objspace.std.callmethod import LOOKUP_METHOD, CALL_METHOD
        StdObjSpaceFrame.LOOKUP_METHOD = LOOKUP_METHOD
        StdObjSpaceFrame.CALL_METHOD = CALL_METHOD
    if space.config.objspace.std.optimized_comparison_op:
        StdObjSpaceFrame.COMPARE_OP = fast_COMPARE_OP
    if space.config.objspace.std.logspaceoptypes:
        assert 0, "logspaceoptypes: a few fixes a missing here"
        StdObjSpace._space_op_types = []
        for name, new in get_logging():
            setattr(StdObjSpaceFrame, name, new)
    return StdObjSpaceFrame


def get_logging():
    for name, func in pyframe.PyFrame.__dict__.iteritems():
        if hasattr(func, 'binop'):
            operationname = func.binop
            def make_opimpl(operationname):
                def opimpl(f, *ignored):
                    operation = getattr(f.space, operationname)
                    w_2 = f.popvalue()
                    w_1 = f.popvalue()
                    if we_are_translated():
                        s = operationname + ' ' + str(w_1) + ' ' + str(w_2)
                    else:
                        names = (w_1.__class__.__name__ + ' ' +
                                 w_2.__class__.__name__)
                        s = operationname + ' ' + names
                    f._space_op_types.append(s)
                    w_result = operation(w_1, w_2)
                    f.pushvalue(w_result)
                return func_with_new_name(opimpl,
                                          "opcode_impl_for_%s" % operationname)
            yield name, make_opimpl(operationname)
        elif hasattr(func, 'unaryop'):
            operationname = func.unaryop
            def make_opimpl(operationname):
                def opimpl(f, *ignored):
                    operation = getattr(f.space, operationname)
                    w_1 = f.popvalue()
                    if we_are_translated():
                        s = operationname + ' ' + str(w_1)
                    else:
                        s = operationname + ' ' + w_1.__class__.__name__
                    f._space_op_types.append(s)
                    w_result = operation(w_1)
                    f.pushvalue(w_result)
                return func_with_new_name(opimpl,
                                          "opcode_impl_for_%s" % operationname)
            yield name, make_opimpl(operationname)
