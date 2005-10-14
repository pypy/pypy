from pypy.rpython.l3interp import l3interp
from pypy.rpython.l3interp import model

def test_very_simple():
    op = model.Operation(l3interp.LLFrame.op_int_add, 0, [-1, -2])
    returnlink = model.ReturnLink(None, [])
    block = model.Block([], model.ONE_EXIT, [returnlink])
    block.operations.append(op)
    startlink = model.Link(block, [])
    graph = model.Graph("testgraph", startlink)
    graph.set_constants_int([3, 4])
    g = model.Globals()
    g.graphs = [graph]
    interp = l3interp.LLInterpreter()
    result = interp.eval_graph_int(graph, [])
    assert result == 7
    
