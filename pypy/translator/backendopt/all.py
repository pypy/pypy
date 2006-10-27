from pypy.translator.backendopt.raisingop2direct_call import raisingop2direct_call
from pypy.translator.backendopt import removenoops
from pypy.translator.backendopt import inline
from pypy.translator.backendopt.malloc import remove_simple_mallocs
from pypy.translator.backendopt.constfold import constant_fold_graph
from pypy.translator.backendopt.stat import print_statistics
from pypy.translator.backendopt.merge_if_blocks import merge_if_blocks
from pypy.translator import simplify
from pypy.translator.backendopt.escape import malloc_to_stack
from pypy.translator.backendopt.mallocprediction import clever_inlining_and_malloc_removal
from pypy.translator.backendopt.support import log
from pypy.objspace.flow.model import checkgraph

def backend_optimizations(translator, graphs=None,
                                      raisingop2direct_call_all=False,
                                      inline_threshold=1,
                                      mallocs=True,
                                      merge_if_blocks_to_switch=True,
                                      constfold=True,
                                      heap2stack=False,
                                      clever_malloc_removal=False):

    config = translator.config.translation.backendopt
    # ZZZ the arguments here should disappear
    raisingop2direct_call_all = (config.raisingop2direct_call or
        raisingop2direct_call_all)
    mallocs = config.mallocs or mallocs
    merge_if_blocks_to_switch = (config.merge_if_blocks or
        merge_if_blocks_to_switch)
    constfold = config.constfold or constfold
    heap2stack = config.heap2stack or heap2stack
    clever_malloc_removal = config.clever_malloc_removal or clever_malloc_removal

    if graphs is None:
        graphs = translator.graphs

    if config.print_statistics:
        print "before optimizations:"
        print_statistics(translator.graphs[0], translator, "per-graph.txt")

    if raisingop2direct_call_all:
        raisingop2direct_call(translator, graphs)

    # remove obvious no-ops
    for graph in graphs:
        removenoops.remove_same_as(graph)
        simplify.eliminate_empty_blocks(graph)
        simplify.transform_dead_op_vars(graph, translator)
        removenoops.remove_duplicate_casts(graph, translator)

    if config.print_statistics:
        print "after no-op removal:"
        print_statistics(translator.graphs[0], translator)

    if not clever_malloc_removal:
        # inline functions in each other
        if inline_threshold:
            callgraph = inline.inlinable_static_callers(graphs)
            inline.auto_inlining(translator, inline_threshold,
                                 callgraph=callgraph)
            for graph in graphs:
                removenoops.remove_superfluous_keep_alive(graph)
                removenoops.remove_duplicate_casts(graph, translator)

        if config.print_statistics:
            print "after inlining:"
            print_statistics(translator.graphs[0], translator)

        # vaporize mallocs
        if mallocs:
            tot = 0
            for graph in graphs:
                count = remove_simple_mallocs(graph)
                if count:
                    # remove typical leftovers from malloc removal
                    removenoops.remove_same_as(graph)
                    simplify.eliminate_empty_blocks(graph)
                    simplify.transform_dead_op_vars(graph, translator)
                    tot += count
            log.malloc("removed %d simple mallocs in total" % tot)

        if config.print_statistics:
            print "after malloc removal:"
            print_statistics(translator.graphs[0], translator)
    else:
        assert graphs is translator.graphs  # XXX for now
        clever_inlining_and_malloc_removal(translator)

        if config.print_statistics:
            print "after clever inlining and malloc removal"
            print_statistics(translator.graphs[0], translator)

    if constfold:
        for graph in graphs:
            constant_fold_graph(graph)

    if heap2stack:
        assert graphs is translator.graphs  # XXX for now
        malloc_to_stack(translator)

    if merge_if_blocks_to_switch:
        for graph in graphs:
            merge_if_blocks(graph)

    if config.print_statistics:
        print "after if-to-switch:"
        print_statistics(translator.graphs[0], translator)

    for graph in graphs:
        checkgraph(graph)
