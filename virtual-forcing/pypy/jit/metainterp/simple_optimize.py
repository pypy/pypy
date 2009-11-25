
""" Simplified optimize.py
"""

from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp import resume, compile

EMPTY_VALUES = {}

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
                descr = op.descr
                assert isinstance(descr, compile.ResumeGuardDescr)
                modifier = resume.ResumeDataVirtualAdder(descr, memo)
                newboxes = modifier.finish(EMPTY_VALUES)
                descr.store_final_boxes(op, newboxes)
            newoperations.append(op)
        loop.operations = newoperations
        return None

def optimize_bridge(metainterp_sd, old_loops, loop):
    optimize_loop(metainterp_sd, [], loop)
    return old_loops[0]
