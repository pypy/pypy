from pypy.rpython.l3interp import l3interp
from pypy.rpython.l3interp import model
from pypy.translator.c.test.test_genc import compile
from pypy.translator.translator import TranslationContext
from pypy.annotation import policy

def translate(func, inputargs):
    t = TranslationContext()
    pol = policy.AnnotatorPolicy()
    pol.allow_someobjects = False
    t.buildannotator(policy=pol).build_types(func, inputargs)
    t.buildrtyper().specialize()

    from pypy.translator.tool.cbuild import skip_missing_compiler
    from pypy.translator.c import genc
    builder = genc.CExtModuleBuilder(t, func)
    builder.generate_source()
    skip_missing_compiler(builder.compile)
    builder.import_module()
    return builder.get_entry_point()


#----------------------------------------------------------------------
def eval_seven():
    #def f():
    #    return 3 + 4
    op = model.Operation(l3interp.LLFrame.op_int_add, 0, [-1, -2])
    returnlink = model.ReturnLink()
    block = model.Block()
    block.exitswitch = model.ONE_EXIT
    block.exits = [returnlink]
    block.operations.append(op)
    startlink = model.Link(block, [])
    graph = model.Graph("testgraph", startlink)
    graph.set_constants_int([3, 4])
    g = model.Globals()
    g.graphs = [graph]
    interp = l3interp.LLInterpreter(g)
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
    block = model.Block()
    block.exitswitch = model.ONE_EXIT
    block.exits = [returnlink]
    block.operations.append(op)
    startlink = model.Link(target=block)
    startlink.move_int_registers = [0, 0]
    graph = model.Graph("testgraph", startlink)
    graph.set_constants_int([4])
    g = model.Globals()
    g.graphs = [graph]
    interp = l3interp.LLInterpreter(g)
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
    block = model.Block()
    block.exitswitch = 1
    block.exits = [returnlink1, returnlink2]
    block.operations.append(op)
    startlink = model.Link(target=block)
    startlink.move_int_registers = [0, 0]
    graph = model.Graph("testgraph", startlink)
    graph.set_constants_int([1, 2])
    g = model.Globals()
    g.graphs = [graph]
    interp = l3interp.LLInterpreter(g)
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

#----------------------------------------------------------------------

def eval_call(number):
    #XXX uh: this isn't funny anymore
    #def g(x):
    #    return x + 1
    #def f(x):
    #    return g(x) + 2
    op_g = model.Operation(l3interp.LLFrame.op_int_add, 1, [0, -1])
    op_f = model.Operation(l3interp.LLFrame.op_int_add, 2, [1, -1])
    call_op = model.Operation(l3interp.LLFrame.op_call_graph_int, 1, [0, 0])
    returnlink_g = model.ReturnLink(1)
    returnlink_f = model.ReturnLink(2)
    block_g = model.Block()
    block_g.exitswitch = model.ONE_EXIT
    block_g.exits = [returnlink_g]
    block_g.operations.append(op_g)
    startlink_g = model.StartLink(target=block_g)
    startlink_g.move_int_registers = [0, 0]
    graph_g = model.Graph("g", startlink_g)
    graph_g.set_constants_int([1])

    block_f = model.Block()
    block_f.exitswitch = model.ONE_EXIT
    block_f.exits = [returnlink_f]
    block_f.operations.extend([call_op, op_f])
    startlink_f = model.StartLink(target=block_f)
    startlink_f.move_int_registers = [0, 0]
    graph_f = model.Graph("f", startlink_f)
    graph_f.set_constants_int([2])
    g = model.Globals()
    g.graphs = [graph_g, graph_f]
    interp = l3interp.LLInterpreter(g)
    return interp.eval_graph_int(graph_f, [number])

def test_call():
    result = eval_call(4)
    assert result == 7
    result = eval_call(0)
    assert result == 3

def test_call_translated():
    fn = translate(eval_call, [int]) 
    assert fn(4) == 7 
    assert fn(0) == 3


