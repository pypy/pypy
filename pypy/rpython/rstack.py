"""
This file defines utilities for manipulating the stack in an
RPython-compliant way, intended mostly for use by the Stackless PyPy.
"""

import inspect

def stack_unwind():
    raise RuntimeError("cannot unwind stack in non-translated versions")

def stack_capture():
    raise RuntimeError("cannot unwind stack in non-translated versions")

def stack_frames_depth():
    return len(inspect.stack())

def stack_too_big():
    return False

def stack_check():
    if stack_too_big():
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


from pypy.rpython.extregistry import ExtRegistryEntry

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

class ResumeStateCreateFnEntry(ExtRegistryEntry):
    _about_ = resume_state_create

    def compute_result_annotation(self, s_prevstate, s_label, *args_s):
        from pypy.annotation import model as annmodel
        return annmodel.SomeExternalObject(frame_stack_top)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.rmodel import SimplePointerRepr
        from pypy.translator.stackless.frame import STATE_HEADER

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
        
        
