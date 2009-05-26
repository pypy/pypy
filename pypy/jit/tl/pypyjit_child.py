from pypy.conftest import option
from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp import warmspot
#from pypy.jit.metainterp.simple_optimize import Optimizer
#from pypy.jit.metainterp import optimize as Optimizer
from pypy.jit.metainterp.optimize2 import Optimizer
from pypy.module.pypyjit.policy import PyPyJitPolicy

# Current output: http://paste.pocoo.org/show/106540/
#
# Some optimizations missing:
#
#   - remove the useless 'ec' argument (p1 and p115 in the trace)
#
#   - the guards have very long 'liveboxes' lists containing mostly
#     Consts -- make sure that these Consts are not stored, or else
#     remove them entirely

# Some optimizations that might help under different circumstances:
#
#   - figure out who calls W_TypeObject.is_heaptype(), leading to
#     the "int_and 512" (lines 48, 147, 154)
#
#   - improve the optimization: e.g. ooisnull followed by oononnull
#     on the same variable
#


def run_child(glob, loc):
    import sys, pdb
    interp = loc['interp']
    graph = loc['graph']
    interp.malloc_check = False

    def returns_null(T, *args, **kwds):
        return lltype.nullptr(T)
    interp.heap.malloc_nonmovable = returns_null     # XXX

    print 'warmspot.jittify_and_run() started...'
    from pypy.jit.backend.llgraph.runner import LLtypeCPU
    policy = PyPyJitPolicy(interp.typer.annotator.translator)
    option.view = True
    warmspot.jittify_and_run(interp, graph, [], policy=policy,
                             listops=True, CPUClass=LLtypeCPU,
                             optimizer=Optimizer)


def run_child_ootype(glob, loc):
    import sys, pdb
    interp = loc['interp']
    graph = loc['graph']

    print 'warmspot.jittify_and_run() started...'
    from pypy.jit.backend.llgraph.runner import OOtypeCPU
    policy = PyPyJitPolicy(interp.typer.annotator.translator)
    option.view = True
    warmspot.jittify_and_run(interp, graph, [], policy=policy,
                             listops=True, CPUClass=OOtypeCPU,
                             optimizer=Optimizer)
