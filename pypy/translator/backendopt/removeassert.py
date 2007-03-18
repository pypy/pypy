from pypy.objspace.flow.model import Constant, checkgraph, c_last_exception
from pypy.rpython.rtyper import LowLevelOpList, inputconst
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
#from pypy.translator.simplify import transform_dead_op_vars
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rclass
from pypy.translator.backendopt.support import log


def remove_asserts(translator, graphs):
    rtyper = translator.rtyper
    clsdef = translator.annotator.bookkeeper.getuniqueclassdef(AssertionError)
    r_AssertionError = rclass.getclassrepr(rtyper, clsdef)
    ll_AssertionError = r_AssertionError.convert_const(AssertionError)

    for graph in graphs:
        count = 0
        morework = True
        while morework:
            morework = False
            eliminate_empty_blocks(graph)
            join_blocks(graph)
            for link in graph.iterlinks():
                if (link.target is graph.exceptblock
                    and isinstance(link.args[0], Constant)
                    and link.args[0].value == ll_AssertionError):
                    if kill_assertion_link(graph, link):
                        count += 1
                        morework = True
                        break
                    else:
                        log.removeassert("cannot remove an assert from %s" % (graph.name,))
        if count:
            # now melt away the (hopefully) dead operation that compute
            # the condition
            if translator.config.translation.verbose:
                log.removeassert("removed %d asserts in %s" % (count, graph.name))
            checkgraph(graph)
            #transform_dead_op_vars(graph, translator)


def kill_assertion_link(graph, link):
    block = link.prevblock
    exits = list(block.exits)
    if len(exits) <= 1:
        return False
    remove_condition = len(exits) == 2
    if block.exitswitch == c_last_exception:
        if link is exits[0]:
            return False       # cannot remove the non-exceptional path
    else:
        if block.exitswitch.concretetype is not lltype.Bool:   # a switch
            remove_condition = False
        else:
            # common case: if <cond>: raise AssertionError
            # turn it into a debug_assert operation
            assert remove_condition
            newops = LowLevelOpList()
            if link.exitcase:
                v = newops.genop('bool_not', [block.exitswitch],
                                 resulttype = lltype.Bool)
            else:
                v = block.exitswitch
            msg = "assertion failed in %s" % (graph.name,)
            c_msg = inputconst(lltype.Void, msg)
            newops.genop('debug_assert', [v, c_msg])
            block.operations.extend(newops)

    exits.remove(link)
    if remove_condition:
        # condition no longer necessary
        block.exitswitch = None
        exits[0].exitcase = None
        exits[0].llexitcase = None
    block.recloseblock(*exits)
    return True
