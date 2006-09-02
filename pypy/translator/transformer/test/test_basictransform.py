
""" test basic javascript transformation
"""

from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.transformer.basictransform import BasicTransformer
from pypy import conftest
from pypy.rpython import llinterp
from pypy.objspace.flow import model
from pypy.translator.unsimplify import copyvar

def transform_function(transformerclass, fun, annotation=[], specialize=True,
    type_system="ootype"):
    t = TranslationContext()
    annotator = t.buildannotator()
    annotator.build_types(fun, annotation)
    tran = transformerclass(t)
    tran.transform_all()
    
    if conftest.option.view:
        t.view()
    
    t.buildrtyper(type_system=type_system).specialize()
    
    if conftest.option.view:
        t.view()
    
    return t

def interp_fun(t, fun, args=[]):
    graph = graphof(t, fun)
    interp = llinterp.LLInterpreter(t.rtyper)
    res = interp.eval_graph(graph, args)
    return res

class OpTransformer(BasicTransformer):
    def transform_graph(self, graph):
        block = graph.startblock
        op, v = self.genop("add", [(1, True), (2, True)])
        block.operations.append(op)
        self.add_block(graph, block)
        block.exits[0].args = [v]
    
def test_genop():
    def genop_fun(i1, i2):
        return 1
    
    t = transform_function(OpTransformer, genop_fun, [int, int])
    res = interp_fun(t, genop_fun, [3, 2])
    assert res == 3

class BlockTransformer(BasicTransformer):
    def transform_graph(self, graph):
        block = model.Block(graph.startblock.inputargs[:])
        
        old_start_block = graph.startblock
        graph.startblock = block
        
        block.isstartblock = True
        old_start_block.isstartblock = False
        op, v = self.genop("add", (block.inputargs[0], (1, True)))
        block.operations.append(op)
        block.closeblock(model.Link([v], old_start_block))
        
        self.add_block(graph, block)
        
        old_start_block.renamevariables({block.inputargs[0]: 
            copyvar(self.annotator, block.inputargs[0])})

def test_change_startblock():
    def some_fun(i):
        return i
    
    t = transform_function(BlockTransformer, some_fun, [int])
    res = interp_fun(t, some_fun, [1])
    assert res == 2

class ClassHelper(object):
    def __init__(self):
        self.i = 0
    
    def method(self):
        self.i = 8

helper_instance = ClassHelper()

class HelperTransformer(BasicTransformer):
    def __init__(self, translator):
        BasicTransformer.__init__(self, translator)
        self.flow_method(ClassHelper, 'method', [])
        bk = self.bookkeeper
        self.instance_const = model.Constant(helper_instance, \
            concretetype=bk.immutablevalue(helper_instance))
        
    def transform_graph(self, graph):
        if graph.name != 'helper_call_fun':
            return
        block = graph.startblock
        c = self.get_const("method")
        op, v = self.genop("getattr", [self.instance_const, c])
        block.operations.insert(0, op)
        op, v2 = self.genop("simple_call", [v])
        block.operations.insert(1, op)
        
        self.add_block(graph, block)

def test_method_helper():
    # XXX: retval of method is still wrong
    def helper_call_fun():
        return helper_instance.i
    
    t = transform_function(HelperTransformer, helper_call_fun)
    res = interp_fun(t, helper_call_fun)
    assert res == 8


##def test_transform():
##    def fun(i):
##        a = 3 + i
##        b = a - 1
##        return b
##    
##    def wrapper(i):
##        retval = fun(i)
##        return retval, main_exception_helper.traceback()
##    
##    t = transform_function(wrapper, [int])
##    res = interp_fun(t, wrapper, [3])
##    retval = res._items['item0']
##    traceback = res._items['item1']
##    real_traceback = [i._str for i in traceback._list]
##    assert retval == fun(3)
##    assert len(real_traceback) == 3
##    # XXX: to be fixed as basic_transform continues to grow
