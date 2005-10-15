from pypy.rpython.l3interp import l3interp
from pypy.rpython.l3interp import model
from pypy.translator.c.test.test_genc import compile
from pypy.translator.translator import Translator
from pypy.annotation import policy

def translate(func, inputargs):
    t = Translator(func)
    pol = policy.AnnotatorPolicy()
    pol.allow_someobjects = False
    t.annotate(inputargs, policy=pol)
    t.specialize()
    return t.ccompile() 

#----------------------------------------------------------------------
def eval_seven():
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
    return interp.eval_graph_int(graph, [])
      

def test_very_simple():
    result = eval_seven()
    assert result == 7

def test_very_simple_translated():
    fn = translate(eval_seven, []) 
    assert fn() == 7

#----------------------------------------------------------------------
def eval_eight(number):
    op = model.Operation(l3interp.LLFrame.op_int_add, 1, [0, -1])
    returnlink = model.ReturnLink(target=None)
    returnlink.move_int_registers = [1, 0]
    block = model.Block([], model.ONE_EXIT, [returnlink])
    block.operations.append(op)
    startlink = model.Link(target=block)
    startlink.move_int_registers = [0, 0]
    graph = model.Graph("testgraph", startlink)
    graph.set_constants_int([4])
    g = model.Globals()
    g.graphs = [graph]
    interp = l3interp.LLInterpreter()
    return interp.eval_graph_int(graph, [number])

def test_simple():
    result = eval_eight(4)
    assert result == 8

def test_simple_translated():
    fn = translate(eval_eight, [int]) 
    assert fn(4) == 8 
