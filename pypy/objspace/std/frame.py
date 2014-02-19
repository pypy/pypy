"""StdObjSpace custom opcode implementations"""

from rpython.rlib.rarithmetic import ovfcheck

from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.error import oefmt
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import W_ListObject


class BaseFrame(PyFrame):
    """These opcodes are always overridden."""

    def LIST_APPEND(self, oparg, next_instr):
        w = self.popvalue()
        v = self.peekvalue(oparg - 1)
        if type(v) is W_ListObject:
            v.append(w)
        else:
            raise AssertionError


def int_BINARY_ADD(self, oparg, next_instr):
    space = self.space
    w_2 = self.popvalue()
    w_1 = self.popvalue()
    if type(w_1) is W_IntObject and type(w_2) is W_IntObject:
        try:
            z = ovfcheck(w_1.intval + w_2.intval)
        except OverflowError:
            w_result = w_1.descr_add(space, w_2)
        else:
            w_result = space.newint(z)
    else:
        w_result = space.add(w_1, w_2)
    self.pushvalue(w_result)


def list_BINARY_SUBSCR(self, oparg, next_instr):
    space = self.space
    w_2 = self.popvalue()
    w_1 = self.popvalue()
    if type(w_1) is W_ListObject and type(w_2) is W_IntObject:
        try:
            w_result = w_1.getitem(w_2.intval)
        except IndexError:
            raise oefmt(space.w_IndexError, "list index out of range")
    else:
        w_result = space.getitem(w_1, w_2)
    self.pushvalue(w_result)


def build_frame(space):
    """Consider the objspace config and return a patched frame object."""
    class StdObjSpaceFrame(BaseFrame):
        pass
    if space.config.objspace.std.optimized_int_add:
        StdObjSpaceFrame.BINARY_ADD = int_BINARY_ADD
    if space.config.objspace.std.optimized_list_getitem:
        StdObjSpaceFrame.BINARY_SUBSCR = list_BINARY_SUBSCR
    from pypy.objspace.std.callmethod import LOOKUP_METHOD, CALL_METHOD
    StdObjSpaceFrame.LOOKUP_METHOD = LOOKUP_METHOD
    StdObjSpaceFrame.CALL_METHOD = CALL_METHOD
    return StdObjSpaceFrame
