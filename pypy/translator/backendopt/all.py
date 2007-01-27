from pypy.translator.backendopt.raisingop2direct_call import raisingop2direct_call
from pypy.translator.backendopt import removenoops
from pypy.translator.backendopt import inline
from pypy.translator.backendopt.malloc import remove_mallocs
from pypy.translator.backendopt.constfold import constant_fold_graph
from pypy.translator.backendopt.stat import print_statistics
from pypy.translator.backendopt.merge_if_blocks import merge_if_blocks
from pypy.translator import simplify
from pypy.translator.backendopt.escape import malloc_to_stack
from pypy.translator.backendopt import mallocprediction
from pypy.translator.backendopt.removeassert import remove_asserts
from pypy.translator.backendopt.support import log
from pypy.translator.backendopt.checkvirtual import check_virtual_methods
from pypy.objspace.flow.model import checkgraph

INLINE_THRESHOLD_FOR_TEST = 33

def backend_optimizations(translator, graphs=None, secondary=False, **kwds):
    # sensible keywords are
    # raisingop2direct_call, inline_threshold, mallocs
    # merge_if_blocks, constfold, heap2stack
    # clever_malloc_removal, remove_asserts

    config = translator.config.translation.backendopt.copy()
    config.set(**kwds)

    if graphs is None:
        graphs = translator.graphs

    if config.print_statistics:
        print "before optimizations:"
        print_statistics(translator.graphs[0], translator, "per-graph.txt")

    if config.raisingop2direct_call:
        raisingop2direct_call(translator, graphs)

    if translator.rtyper.type_system.name == 'ootypesystem':
        check_virtual_methods()

    # remove obvious no-ops
    for graph in graphs:
        removenoops.remove_same_as(graph)
        simplify.eliminate_empty_blocks(graph)
        simplify.transform_dead_op_vars(graph, translator)
        removenoops.remove_duplicate_casts(graph, translator)

    if config.print_statistics:
        print "after no-op removal:"
        print_statistics(translator.graphs[0], translator)

    if not config.clever_malloc_removal:
        if config.profile_based_inline and not secondary:
            inline_malloc_removal_phase(config, translator, graphs,
                                        config.inline_threshold*.5) # xxx tune!
            inline.instrument_inline_candidates(graphs, config.inline_threshold)
            counters = translator.driver_instrument_result(
                       config.profile_based_inline)
            n = len(counters)
            def call_count_pred(label):
                if label >= n:
                    return False
                return counters[label] > 250 # xxx tune!
        else:
            call_count_pred = None
        inline_malloc_removal_phase(config, translator, graphs,
                                    config.inline_threshold,
                                    call_count_pred=call_count_pred)
    else:
        count = mallocprediction.preparation(translator, graphs)
        count += mallocprediction.clever_inlining_and_malloc_removal(
            translator, graphs)
        log.inlineandremove("removed %d simple mallocs in total" % count)
        if config.print_statistics:
            print "after clever inlining and malloc removal"
            print_statistics(translator.graphs[0], translator)

    if config.constfold:
        for graph in graphs:
            constant_fold_graph(graph)

    if config.remove_asserts:
        remove_asserts(translator, graphs)

    if config.heap2stack:
        assert graphs is translator.graphs  # XXX for now
        malloc_to_stack(translator)

    if config.merge_if_blocks:
        for graph in graphs:
            merge_if_blocks(graph)

    if config.print_statistics:
        print "after if-to-switch:"
        print_statistics(translator.graphs[0], translator)

    for graph in graphs:
        checkgraph(graph)

def inline_malloc_removal_phase(config, translator, graphs, inline_threshold,
                                call_count_pred=None):

    type_system = translator.rtyper.type_system.name
    log.inlining("phase with threshold factor: %s" % inline_threshold)

    # inline functions in each other
    if inline_threshold:
        inline.auto_inline_graphs(translator, graphs, inline_threshold,
                                  call_count_pred=call_count_pred)

        if config.print_statistics:
            print "after inlining:"
            print_statistics(translator.graphs[0], translator)

    # vaporize mallocs
    if config.mallocs:
        remove_mallocs(translator, graphs, type_system)

        if config.print_statistics:
            print "after malloc removal:"
            print_statistics(translator.graphs[0], translator)    

    if config.constfold:
        for graph in graphs:
            constant_fold_graph(graph)

