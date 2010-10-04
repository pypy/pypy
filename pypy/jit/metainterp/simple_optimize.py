
""" Simplified optimize.py
"""

from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp import resume, compile

EMPTY_VALUES = {}

def transform(op):
    from pypy.jit.metainterp.history import AbstractDescr
    # Rename CALL_PURE and CALL_INVARIANT to CALL.
    # Simplify the VIRTUAL_REF_* so that they don't show up in the backend.
    if (op.getopnum() == rop.CALL_PURE or
        op.getopnum() == rop.CALL_LOOPINVARIANT):
        op = ResOperation(rop.CALL, op.getarglist()[1:], op.result,
                          op.getdescr())
    elif op.getopnum() == rop.VIRTUAL_REF:
        op = ResOperation(rop.SAME_AS, [op.getarg(0)], op.result)
    elif op.getopnum() == rop.VIRTUAL_REF_FINISH:
        return []
    return [op]

def optimize_loop(metainterp_sd, old_loops, loop):
    if old_loops:
        assert len(old_loops) == 1
        return old_loops[0]
    else:
        # copy loop operations here
        # we need it since the backend can modify those lists, which make
        # get_guard_op in compile.py invalid
        # in fact, x86 modifies this list for moving GCs
        memo = resume.ResumeDataLoopMemo(metainterp_sd)
        newoperations = []
        for op in loop.operations:
            if op.is_guard():
                descr = op.getdescr()
                assert isinstance(descr, compile.ResumeGuardDescr)
                modifier = resume.ResumeDataVirtualAdder(descr, memo)
                newboxes = modifier.finish(EMPTY_VALUES)
                descr.store_final_boxes(op, newboxes)
            newoperations.extend(transform(op))
        loop.operations = newoperations
        return None

def optimize_bridge(metainterp_sd, old_loops, loop):
    optimize_loop(metainterp_sd, [], loop)
    return old_loops[0]
