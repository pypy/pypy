"""
This file defines utilities for manipulating the stack in an
RPython-compliant way, intended mostly for use by the Stackless PyPy.
"""

import inspect

from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.controllerentry import Controller, SomeControlledInstance
from pypy.translator.tool.cbuild import ExternalCompilationInfo

def stack_unwind():
    if we_are_translated():
        from pypy.rpython.lltypesystem.lloperation import llop
        return llop.stack_unwind(lltype.Void)
    raise RuntimeError("cannot unwind stack in non-translated versions")


def stack_capture():
    if we_are_translated():
        from pypy.rpython.lltypesystem.lloperation import llop
        ptr = llop.stack_capture(OPAQUE_STATE_HEADER_PTR)
        return frame_stack_top_controller.box(ptr)
    raise RuntimeError("cannot unwind stack in non-translated versions")


def stack_frames_depth():
    if we_are_translated():
        from pypy.rpython.lltypesystem.lloperation import llop
        return llop.stack_frames_depth(lltype.Signed)
    else:
        return len(inspect.stack())

compilation_info = ExternalCompilationInfo(includes=['src/stack.h'])

stack_too_big = rffi.llexternal('LL_stack_too_big', [], rffi.INT,
                                compilation_info=compilation_info,
                                _nowrapper=True,
                                _callable=lambda: 0,
                                sandboxsafe=True)

def stack_check():
    if rffi.cast(lltype.Signed, stack_too_big()):
        # stack_unwind implementation is different depending on if stackless
        # is enabled. If it is it unwinds the stack, otherwise it simply
        # raises a RuntimeError.
        stack_unwind()

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


def resume_point(label, *args, **kwds):
    pass



class ResumePointFnEntry(ExtRegistryEntry):
    _about_ = resume_point

    def compute_result_annotation(self, s_label, *args_s, **kwds_s):
        from pypy.annotation import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        from pypy.objspace.flow import model

        assert hop.args_s[0].is_constant()
        c_label = hop.inputconst(lltype.Void, hop.args_s[0].const)
        args_v = hop.args_v[1:]
        if 'i_returns' in kwds_i:
            assert len(kwds_i) == 1
            returns_index = kwds_i['i_returns']
            v_return = args_v.pop(returns_index-1)
            assert isinstance(v_return, model.Variable), \
                   "resume_point returns= argument must be a Variable"
        else:
            assert not kwds_i
            v_return = hop.inputconst(lltype.Void, None)

        for v in args_v:
            assert isinstance(v, model.Variable), "resume_point arguments must be Variables"

        hop.exception_is_here()
        return hop.genop('resume_point', [c_label, v_return] + args_v,
                         hop.r_result)

def resume_state_create(prevstate, label, *args):
    raise RuntimeError("cannot resume states in non-translated versions")

def concretify_argument(hop, index):
    from pypy.objspace.flow import model

    v_arg = hop.args_v[index]
    if isinstance(v_arg, model.Variable):
        return v_arg

    r_arg = hop.rtyper.bindingrepr(v_arg)
    return hop.inputarg(r_arg, arg=index)

class ResumeStateCreateFnEntry(FrameStackTopReturningFnEntry):
    _about_ = resume_state_create

    def compute_result_annotation(self, s_prevstate, s_label, *args_s):
        return FrameStackTopReturningFnEntry.compute_result_annotation(self)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype

        assert hop.args_s[1].is_constant()
        c_label = hop.inputconst(lltype.Void, hop.args_s[1].const)

        v_state = hop.inputarg(hop.r_result, arg=0)

        args_v = []
        for i in range(2, len(hop.args_v)):
            args_v.append(concretify_argument(hop, i))

        hop.exception_is_here()
        return hop.genop('resume_state_create', [v_state, c_label] + args_v,
                         hop.r_result)

def resume_state_invoke(type, state, **kwds):
    raise NotImplementedError("only works in translated versions")

class ResumeStateInvokeFnEntry(ExtRegistryEntry):
    _about_ = resume_state_invoke

    def compute_result_annotation(self, s_type, s_state, **kwds):
        from pypy.annotation.bookkeeper import getbookkeeper
        assert s_type.is_constant()
        return getbookkeeper().valueoftype(s_type.const)

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        v_state = hop.args_v[1]
        
        if 'i_returning' in kwds_i:
            assert len(kwds_i) == 1
            returning_index = kwds_i['i_returning']
            v_returning = concretify_argument(hop, returning_index)
            v_raising = hop.inputconst(lltype.Void, None)
        elif 'i_raising' in kwds_i:
            assert len(kwds_i) == 1
            raising_index = kwds_i['i_raising']
            v_returning = hop.inputconst(lltype.Void, None)
            v_raising = concretify_argument(hop, raising_index)
        else:
            assert not kwds_i
            v_returning = hop.inputconst(lltype.Void, None)
            v_raising = hop.inputconst(lltype.Void, None)

        hop.exception_is_here()
        return hop.genop('resume_state_invoke', [v_state, v_returning, v_raising],
                         hop.r_result)
        
