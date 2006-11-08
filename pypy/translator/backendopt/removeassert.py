from pypy.objspace.flow.model import Constant
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rclass


def remove_asserts(translator, graphs):
    rtyper = translator.rtyper
    clsdef = translator.annotator.bookkeeper.getuniqueclassdef(AssertionError)
    r_AssertionError = rclass.getclassrepr(rtyper, clsdef)
    ll_AssertionError = r_AssertionError.convert_const(AssertionError)

    while graphs:
        pending = []
        for graph in graphs:
            eliminate_empty_blocks(graph)
            join_blocks(graph)
            for link in graph.iterlinks():
                if (link.target is graph.exceptblock
                    and isinstance(link.args[0], Constant)
                    and link.args[0].value == ll_AssertionError):
                    if kill_assertion_link(graph, link):
                        pending.append(graph)
                        break
        graphs = pending


def kill_assertion_link(graph, link):
    block = link.prevblock
    exits = list(block.exits)
    if len(exits) > 1:
        exits.remove(link)
        if len(exits) == 1 and block.exitswitch.concretetype is lltype.Bool:
            # condition no longer necessary
            block.exitswitch = None
            exits[0].exitcase = None
            exits[0].llexitcase = None
        block.recloseblock(*exits)
        return True
    else:
        return False
