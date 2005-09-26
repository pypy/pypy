import sys
from pypy.translator.unsimplify import copyvar, split_block
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, last_exception
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph, flatten
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import Bool, typeOf, FuncType, _ptr
from pypy.rpython import rmodel

# this transformation is very academical -- I had too much time

def get_graph(arg, translator):
    if isinstance(arg, Variable):
        return None
    f = arg.value
    if not isinstance(f, _ptr):
        return None
    try:
        callable = f._obj._callable
        #external function calls don't have a real graph
        if getattr(callable, "suggested_primitive", False):
            return None
        if callable in translator.flowgraphs:
            return translator.flowgraphs[callable]
    except AttributeError, KeyError:
        pass
    try:
        return f._obj.graph
    except AttributeError:
        return None

def _remove_tail_call(translator, graph, block):
    print "removing tail call"
    assert len(block.exits) == 1
    assert block.exits[0].target is graph.returnblock
    assert block.operations[-1].result == block.exits[0].args[0]
    op = block.operations[-1]
    block.operations = block.operations[:-1]
    block.exits[0].args = op.args[1:]
    block.exits[0].target = graph.startblock

def remove_tail_calls_to_self(translator, graph):
    entrymap = mkentrymap(graph)
    changed = False
    for link in entrymap[graph.returnblock]:
        block = link.prevblock
        if (len(block.exits) == 1 and
            len(block.operations) > 0 and
            block.operations[-1].opname == 'direct_call' and
            block.operations[-1].result == link.args[0]):
            call = get_graph(block.operations[-1].args[0], translator)
            print "getgraph", graph
            if graph is graph:
                _remove_tail_call(translator, graph, block)
                changed = True
    if changed:
        from pypy.translator import simplify
        checkgraph(graph)
        simplify.remove_identical_vars(graph)
        simplify.eliminate_empty_blocks(graph)
        simplify.join_blocks(graph)
