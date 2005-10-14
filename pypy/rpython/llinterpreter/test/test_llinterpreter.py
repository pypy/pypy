from pypy.rpython.llinterpreter import llinterpreter
from pypy.rpython.llinterpreter import model

def test_very_simple():
    op = model.Operation(llinterpreter.LLFrame.op_int_add, 0, [-1, -2])
    returnlink = model.ReturnLink(None, [])
    block = model.Block([], model.ONE_EXIT, [returnlink])
    block.operations.append(op)
    startlink = model.Link(block, [])
    graph = model.Graph("testgraph", startlink)
    graph.set_constants_int([3, 4])
    g = model.Globals()
    g.graphs = [graph]
    l3interp = llinterpreter.LLInterpreter()
    result = l3interp.eval_graph_int(graph, [])
    assert result == 7
    
