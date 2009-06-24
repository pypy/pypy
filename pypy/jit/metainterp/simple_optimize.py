
""" Simplified optimize.py
"""

from pypy.jit.metainterp.resoperation import rop

def optimize_loop(options, old_loops, loop, cpu=None):
    if old_loops:
        assert len(old_loops) == 1
        return old_loops[0]
    else:
        # copy loop operations here
        # we need it since the backend can modify those lists, which make
        # get_guard_op in compile.py invalid
        # in fact, x86 modifies this list for moving GCs
        loop.operations = loop.operations[:]
        return None

def optimize_bridge(options, old_loops, loop, cpu=None):
    optimize_loop(options, [], loop, cpu)
    return old_loops[0]

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)

    @staticmethod
    def get_optimizer_name():
        return __file__
