from pypy.tool.algo import regalloc
from pypy.jit.metainterp.history import getkind
from pypy.jit.codewriter.flatten import ListOfKind


def perform_register_allocation(graph, kind):
    checkkind = lambda v: getkind(v.concretetype) == kind
    return regalloc.perform_register_allocation(graph, checkkind, ListOfKind)
