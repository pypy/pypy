from pypy.objspace.flow.model import checkgraph
from pypy.translator.backendopt.removenoops import remove_same_as
from pypy.translator.backendopt.inline import auto_inlining
from pypy.translator.backendopt.malloc import remove_simple_mallocs
from pypy.translator.backendopt.ssa import SSI_to_SSA
from pypy.translator import simplify


def backend_optimizations(translator, inline_threshold=1, ssa_form=True):
    # remove obvious no-ops
    for graph in translator.flowgraphs.values():
        remove_same_as(graph)
        simplify.eliminate_empty_blocks(graph)

    # inline functions around
    if inline_threshold and 0:  # XXX in progress
        auto_inlining(translator, inline_threshold)

    # vaporize mallocs
    # XXX in progress
    for graph in []:# translator.flowgraphs.values():
        if remove_simple_mallocs(graph):
            # remove typical leftovers from malloc removal
            remove_same_as(graph)
            simplify.eliminate_empty_blocks(graph)
            simplify.transform_dead_op_vars(graph)

    if ssa_form:
        for graph in translator.flowgraphs.values():
            SSI_to_SSA(graph)
