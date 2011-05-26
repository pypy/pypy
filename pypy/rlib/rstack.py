"""
This file defines utilities for manipulating the stack in an
RPython-compliant way, intended mostly for use by the Stackless PyPy.
"""

import inspect

from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib import rgc
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.controllerentry import Controller, SomeControlledInstance
from pypy.translator.tool.cbuild import ExternalCompilationInfo

def stack_unwind():
    if we_are_translated():
        return llop.stack_unwind(lltype.Void)
    raise RuntimeError("cannot unwind stack in non-translated versions")


def stack_capture():
    if we_are_translated():
        ptr = llop.stack_capture(OPAQUE_STATE_HEADER_PTR)
        return frame_stack_top_controller.box(ptr)
    raise RuntimeError("cannot unwind stack in non-translated versions")


def stack_frames_depth():
    if we_are_translated():
        return llop.stack_frames_depth(lltype.Signed)
    else:
        return len(inspect.stack())

# ____________________________________________________________

compilation_info = ExternalCompilationInfo(includes=['src/stack.h'])

def llexternal(name, args, res, _callable=None):
    return rffi.llexternal(name, args, res, compilation_info=compilation_info,
                           sandboxsafe=True, _nowrapper=True,
                           _callable=_callable)

_stack_get_start = llexternal('LL_stack_get_start', [], lltype.Signed,
                              lambda: 0)
_stack_get_length = llexternal('LL_stack_get_length', [], lltype.Signed,
                               lambda: 1)
_stack_set_length_fraction = llexternal('LL_stack_set_length_fraction',
                                        [lltype.Float], lltype.Void,
                                        lambda frac: None)
_stack_too_big_slowpath = llexternal('LL_stack_too_big_slowpath',
                                     [lltype.Signed], lltype.Char,
                                     lambda cur: '\x00')
# the following is used by the JIT
_stack_get_start_adr = llexternal('LL_stack_get_start_adr', [], lltype.Signed)
_stack_get_length_adr= llexternal('LL_stack_get_length_adr',[], lltype.Signed)


def stack_check():
    if not we_are_translated():
        return
    #
    # Load the "current" stack position, or at least some address that
    # points close to the current stack head
    current = llop.stack_current(lltype.Signed)
    #
    # Load these variables from C code
    start = _stack_get_start()
    length = _stack_get_length()
    #
    # Common case: if 'current' is within [start:start+length], everything
    # is fine
    ofs = r_uint(current - start)
    if ofs < r_uint(length):
        return
    #
    # Else call the slow path
    stack_check_slowpath(current)
stack_check._always_inline_ = True

@rgc.no_collect
def stack_check_slowpath(current):
    if ord(_stack_too_big_slowpath(current)):
        # Now we are sure that the stack is really too big.  Note that the
        # stack_unwind implementation is different depending on if stackless
        # is enabled. If it is it unwinds the stack, otherwise it simply
        # raises a RuntimeError.
        stack_unwind()
stack_check_slowpath._dont_inline_ = True

# ____________________________________________________________

def yield_current_frame_to_caller():
    raise NotImplementedError("only works in translated versions")


class frame_stack_top(object):
    def switch(self):
        raise NotImplementedError("only works in translated versions")


class BoundSwitchOfFrameStackTop(object): pass
class BoundSwitchOfFrameStackTopController(Controller):
    knowntype = BoundSwitchOfFrameStackTop
    def call(self, real_object):
        from pypy.rpython.lltypesystem.lloperation import llop
        ptr = llop.stack_switch(OPAQUE_STATE_HEADER_PTR, real_object)
        return frame_stack_top_controller.box(ptr)


class FrameStackTopController(Controller):
    knowntype = frame_stack_top
    can_be_None = True

    def is_true(self, real_object):
        return bool(real_object)

    def get_switch(self, real_object):
        return bound_switch_of_frame_stack_top_controller.box(real_object)

    def convert(self, obj):
        assert obj is None
        return lltype.nullptr(OPAQUE_STATE_HEADER_PTR.TO)

frame_stack_top_controller = FrameStackTopController()
bound_switch_of_frame_stack_top_controller = BoundSwitchOfFrameStackTopController()
OPAQUE_STATE_HEADER = lltype.GcOpaqueType("OPAQUE_STATE_HEADER", hints={"render_structure": True})
OPAQUE_STATE_HEADER_PTR = lltype.Ptr(OPAQUE_STATE_HEADER)



class FrameStackTopReturningFnEntry(ExtRegistryEntry):
    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return SomeControlledInstance(annmodel.lltype_to_annotation(OPAQUE_STATE_HEADER_PTR), frame_stack_top_controller)


class YieldCurrentFrameToCallerFnEntry(FrameStackTopReturningFnEntry):
    _about_ = yield_current_frame_to_caller

    def specialize_call(self, hop):
        var = hop.genop("yield_current_frame_to_caller", [], hop.r_result.lowleveltype)
        return var


# ____________________________________________________________

def get_stack_depth_limit():
    if we_are_translated():
        from pypy.rpython.lltypesystem.lloperation import llop
        return llop.get_stack_depth_limit(lltype.Signed)
    raise RuntimeError("no stack depth limit in non-translated versions")

def set_stack_depth_limit(limit):
    if we_are_translated():
        from pypy.rpython.lltypesystem.lloperation import llop
        return llop.set_stack_depth_limit(lltype.Void, limit)
    raise RuntimeError("no stack depth limit in non-translated versions")
