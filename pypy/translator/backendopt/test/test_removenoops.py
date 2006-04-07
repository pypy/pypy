from pypy.translator.backendopt.removenoops import remove_void, remove_same_as, \
        remove_unaryops, remove_duplicate_casts, remove_superfluous_keep_alive
from pypy.translator.backendopt.inline import inline_function
from pypy.translator.backendopt.test.test_propagate import getops, get_graph, check_graph
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.test.snippet import simple_method
from pypy.objspace.flow.model import checkgraph, flatten, Block
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter
from pypy import conftest

import py
log = py.log.Producer('test_backendoptimization')


def annotate_and_remove_void(f, annotate):
    t = TranslationContext()
    t.buildannotator().build_types(f, annotate)
    t.buildrtyper().specialize()
    remove_void(t)
    return t

def test_remove_void_args():
    def f(i):
        return [1,2,3,i][i]
    t = annotate_and_remove_void(f, [int])
    for graph in t.graphs:
        assert checkgraph(graph) is None
        for arg in graph.startblock.inputargs:
            assert arg.concretetype is not lltype.Void
    interp = LLInterpreter(t.rtyper)
    assert interp.eval_graph(graphof(t, f), [0]) == 1 

def test_remove_void_in_struct():
    t = annotate_and_remove_void(simple_method, [int])
    #t.view()
    for graph in t.graphs:
        log('func : ' + graph.name)
        log('graph: ' + str(graph))
        assert checkgraph(graph) is None
        #for fieldname in self.struct._names:    #XXX helper (in lltype?) should remove these voids
        #    type_ = getattr(struct, fieldname)
        #    log('fieldname=%(fieldname)s , type_=%(type_)s' % locals())
        #    assert _type is not lltype.Void
    #interp = LLInterpreter(t.flowgraphs, t.rtyper)
    #assert interp.eval_function(f, [0]) == 1 

def test_remove_same_as():
    def nothing(x):
        return x
    def f():
        nothing(False)
        if nothing(True):
            return 42
        else:
            return 666
    t = TranslationContext()
    t.buildannotator().build_types(f, [])
    t.buildrtyper().specialize()
    # now we make the 'if True' appear
    f_graph = graphof(t, f)
    inline_function(t, nothing, f_graph)
    # here, the graph looks like  v21=same_as(True);  exitswitch: v21
    remove_same_as(f_graph)
    t.checkgraphs()
    # only one path should be left
    for block in f_graph.iterblocks():
        assert len(block.exits) <= 1

    interp = LLInterpreter(t.rtyper)
    result = interp.eval_graph(f_graph, [])
    assert result == 42

def test_remove_unaryops():
    # We really want to use remove_unaryops for things like ooupcast and
    # oodowncast in dynamically typed languages, but it's easier to test
    # it with operations on ints here.
    def f(x):
        i = llop.int_invert(lltype.Signed, x)
        i = llop.int_add(lltype.Signed, x, 1)
        return llop.int_neg(lltype.Signed, i)
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    f_graph = graphof(t, f)
    remove_unaryops(f_graph, ["int_neg", "int_invert"])
    t.checkgraphs()

    interp = LLInterpreter(t.rtyper)
    result = interp.eval_graph(f_graph, [-2])
    assert result == -1

def test_remove_keepalive():
    S = lltype.GcStruct("s", ("f", lltype.Signed))
    def f():
        s1 = lltype.malloc(S)
        llop.keepalive(lltype.Void, s1)
        s2 = lltype.malloc(S)
        llop.keepalive(lltype.Void, s1)
        llop.keepalive(lltype.Void, s2)
        return id(s1) + id(s2)
    graph, t = get_graph(f, [])
    remove_superfluous_keep_alive(graph)
    ops = getops(graph)
    assert len(ops['keepalive']) == 2

def test_remove_duplicate_casts():
    class A(object):
        def __init__(self, x, y):
            self.x = x
            self.y = y
        def getsum(self):
            return self.x + self.y
    class B(A):
        def __init__(self, x, y, z):
            A.__init__(self, x, y)
            self.z = z
        def getsum(self):
            return self.x + self.y + self.z
    def f(x, switch):
        a = A(x, x + 1)
        b = B(x, x + 1, x + 2)
        if switch:
            c = A(x, x + 1)
        else:
            c = B(x, x + 1, x + 2)
        return a.x + a.y + b.x + b.y + b.z + c.getsum()
    assert f(10, True) == 75
    graph, t = get_graph(f, [int, bool], 1)
    num_cast_pointer = len(getops(graph)['cast_pointer'])
    changed = remove_duplicate_casts(graph, t)
    assert changed
    ops = getops(graph)
    assert len(ops['cast_pointer']) < num_cast_pointer
    print len(ops['cast_pointer']), num_cast_pointer
    graph_getsum = graphof(t, B.getsum.im_func)
    num_cast_pointer = len(getops(graph_getsum)['cast_pointer'])
    changed = remove_duplicate_casts(graph_getsum, t)
    assert changed
    if conftest.option.view:
        t.view()
    check_graph(graph, [10, True], 75, t)
    ops = getops(graph_getsum)
    assert len(ops['cast_pointer']) < num_cast_pointer
    print len(ops['cast_pointer']), num_cast_pointer
    
