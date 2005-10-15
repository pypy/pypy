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
    #def f():
    #    return 3 + 4
    op = model.Operation(l3interp.LLFrame.op_int_add, 0, [-1, -2])
    returnlink = model.ReturnLink()
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
    #def f(x):
    #    return x + 4
    op = model.Operation(l3interp.LLFrame.op_int_add, 1, [0, -1])
    returnlink = model.ReturnLink(return_val=1)
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
#----------------------------------------------------------------------

def eval_branch(number):
    #def f(x):
    #    if x:
    #        return 2
    #    return 1
    op = model.Operation(l3interp.LLFrame.op_int_is_true, 1, [0])
    returnlink1 = model.ReturnLink(-1)
    returnlink2 = model.ReturnLink(-2)
    block = model.Block([], 1, [returnlink1, returnlink2])
    block.operations.append(op)
    startlink = model.Link(target=block)
    startlink.move_int_registers = [0, 0]
    graph = model.Graph("testgraph", startlink)
    graph.set_constants_int([1, 2])
    g = model.Globals()
    g.graphs = [graph]
    interp = l3interp.LLInterpreter()
    return interp.eval_graph_int(graph, [number])

def test_branch():
    result = eval_branch(4)
    assert result == 2
    result = eval_branch(0)
    assert result == 1

def test_branch_translated():
    fn = translate(eval_branch, [int]) 
    assert fn(4) == 2 
    assert fn(0) == 1
