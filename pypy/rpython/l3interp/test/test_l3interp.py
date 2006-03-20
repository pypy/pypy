from pypy.rpython.l3interp import l3interp
from pypy.rpython.l3interp import model
from pypy.rpython.l3interp.model import Op
from pypy.translator.c.test.test_genc import compile
from pypy.translator.translator import TranslationContext
from pypy.annotation import policy
from pypy.rpython.lltypesystem import lltype 
from pypy import conftest

def setup_module(mod):
    mod._cleanups = []

def teardown_module(mod):
    while mod._cleanups:
        mod._cleanups.pop()()

def translate(func, inputargs):
    from pypy.translator.c.gc import BoehmGcPolicy
    t = TranslationContext()
    pol = policy.AnnotatorPolicy()
    pol.allow_someobjects = False
    t.buildannotator(policy=pol).build_types(func, inputargs)
    t.buildrtyper().specialize()
    if conftest.option.view:
        t.view()

    from pypy.translator.tool.cbuild import skip_missing_compiler
    from pypy.translator.c import genc
    builder = genc.CExtModuleBuilder(t, func, gcpolicy=BoehmGcPolicy)
    builder.generate_source()
    skip_missing_compiler(builder.compile)
    builder.isolated_import()
    _cleanups.append(builder.cleanup)
    return builder.get_entry_point()


#----------------------------------------------------------------------
def eval_seven():
    #def f():
    #    return 3 + 4
    block = model.Block([Op.int_add, 0, 1,
                         Op.int_return, -1],
                        constants_int = [3, 4])
    graph = model.Graph("testgraph", block, 0, 0, 0)
    value = l3interp.l3interpret(graph, [], [], [])
    assert isinstance(value, l3interp.L3Integer)
    return value.intval
      
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
    block = model.Block([Op.int_add, -1, 0,
                         Op.int_return, -1],
                        constants_int = [4])
    graph = model.Graph("testgraph", block, 1, 0, 0)
    value = l3interp.l3interpret(graph, [number], [], [])
    assert isinstance(value, l3interp.L3Integer)
    return value.intval

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
    #        return x
    #    return 1
    block1 = model.Block([Op.jump_cond, -1])
    block2 = model.Block([Op.int_return, -1])
    block3 = model.Block([Op.int_return, 0], constants_int=[1])
    block1.exit0 = model.Link(block3)
    block1.exit1 = model.Link(block2, targetregs_int=[-1])
    graph = model.Graph("testgraph", block1, 1, 0, 0)
    value = l3interp.l3interpret(graph, [number], [], [])
    assert isinstance(value, l3interp.L3Integer)
    return value.intval

def test_branch():
    result = eval_branch(4)
    assert result == 4
    result = eval_branch(0)
    assert result == 1

def test_branch_translated():
    fn = translate(eval_branch, [int]) 
    assert fn(4) == 4
    assert fn(0) == 1

#----------------------------------------------------------------------

def eval_call(number):
    #def g(x):
    #    return x + 1
    #def f(x):
    #    return g(x) + 2
    block = model.Block([Op.int_add, -1, 0,
                         Op.int_return, -1],
                        constants_int = [1])
    graph1 = model.Graph("g", block, 1, 0, 0)

    block = model.Block([Op.direct_call, 0, -1,
                         Op.int_add, -1, 0,
                         Op.int_return, -1],
                        constants_int = [2],
                        called_graphs = [graph1])
    graph2 = model.Graph("f", block, 1, 0, 0)

    value = l3interp.l3interpret(graph2, [number], [], [])
    assert isinstance(value, l3interp.L3Integer)
    return value.intval

def test_call():
    result = eval_call(4)
    assert result == 7
    result = eval_call(0)
    assert result == 3

def test_call_translated():
    fn = translate(eval_call, [int]) 
    assert fn(4) == 7 
    assert fn(0) == 3

#----------------------------------------------------------------------

from pypy.rpython.l3interp.test.test_convert import l3ify

def test_getfield():
    class C:
        def __init__(self, x):
            self.x = x
    one = C(1)
    two = C(2)

    def f(n):
        if n:
            return one.x
        else:
            return two.x

    l3graph = l3ify(f, [int])

    def entry_point(x):
        value = l3interp.l3interpret(l3graph, [x], [], [])
        assert isinstance(value, l3interp.L3Integer)
        return value.intval

    assert entry_point(3) == f(3)
    assert entry_point(0) == f(0)

    fn = translate(entry_point, [int])

    assert fn(3) == f(3)
    assert fn(0) == f(0)
        

def test_setfield():
    class C:
        def __init__(self, x):
            self.x = x
    c = C(1)

    def getorset(n):
        if n:
            c.x = n
            return 0
        else:
            return c.x

    getorsetgraph = l3ify(getorset, [int])
    
    def entry_point(x):
        value = l3interp.l3interpret(getorsetgraph, [x], [], [])
        assert isinstance(value, l3interp.L3Integer)
        return value.intval
    
    assert entry_point(-3) == 0
    assert entry_point(0) == -3

    fn = translate(entry_point, [int])

    assert fn(9) == 0
    assert fn(0) == 9


        
def test_getfield_complex():
    class C:
        def __init__(self, x):
            self.x = x
    one = C(1)
    two = C(2)

    class D:
        def __init__(self, c1, c2):
            self.c1 = c1
            self.c2 = c2

    d1 = D(one, two)
    d2 = D(two, one)

    def f(n, m):
        if n:
            if m:
                return d1.c1.x
            else:
                return d1.c2.x
        else:
            if m:
                return d2.c1.x
            else:
                return d2.c2.x

    l3graph = l3ify(f, [int, int])

    def entry_point(x, y):
        value = l3interp.l3interpret(l3graph, [x, y], [], [])
        assert isinstance(value, l3interp.L3Integer)
        return value.intval

    for x in 0, 1:
        for y in 0, 1:
            assert entry_point(x, y) == f(x, y)

    fn = translate(entry_point, [int, int])

    for x in 0, 1:
        for y in 0, 1:
            assert fn(x, y) == f(x, y)


def test_getitem():

    A = lltype.GcArray(lltype.Signed)
    a = lltype.malloc(A, 3)
    a[0] = 1
    a[1] = 2
    a[2] = 3
    

    def f(n):
        return a[n]

    l3graph = l3ify(f, [int])
    def entry_point(x):
        value = l3interp.l3interpret(l3graph, [x], [], [])
        assert isinstance(value, l3interp.L3Integer)
        return value.intval

    for arg in 0,1,2:
        assert entry_point(arg) == f(arg)

    fn = translate(entry_point, [int])
        
    for arg in 0,1,2:
        assert fn(arg) == f(arg)

def test_setitem():

    A = lltype.GcArray(lltype.Signed)
    a = lltype.malloc(A, 3)
    a[0] = 1
    a[1] = 2
    a[2] = 3
    

    def f(index, value):
        if value:
            a[index] = value
            return 0
        return a[index]

    l3graph = l3ify(f, [int, int])
    def entry_point(x, y):
        value = l3interp.l3interpret(l3graph, [x, y], [], [])
        assert isinstance(value, l3interp.L3Integer)
        return value.intval

    entry_point(1, 42)
    assert entry_point(1, 0) == 42
    
    fn = translate(entry_point, [int, int])
        
    entry_point(1, 65)
    assert entry_point(1, 0) == 65

def test_getsetitem_complex():

    A = lltype.GcArray(lltype.Signed)
    AA = lltype.GcArray(lltype.Ptr(A))
    a = lltype.malloc(AA, 3)
    a[0] = lltype.malloc(A, 1)
    a[1] = lltype.malloc(A, 2)
    a[2] = lltype.malloc(A, 3)
    a[0][0] = 1

    a[1][0] = 2
    a[1][1] = 3

    a[2][0] = 4
    a[2][1] = 5
    a[2][2] = 6

    def f(x, y, value):
        if value:
            a[x][y] = value
            return 0
        return a[x][y]
    
    l3graph = l3ify(f, [int, int, int])
    def entry_point(x, y, value):
        value = l3interp.l3interpret(l3graph, [x, y, value], [], [])
        assert isinstance(value, l3interp.L3Integer)
        return value.intval

    for x,y,value in (0,0,0), (0,0,9), (0,0,0), (2,1,0), (2,1,14), (2,1,0):
        assert entry_point(x, y, value) == f(x, y, value)

    
    fn = translate(entry_point, [int, int, int])

    for x,y,value in (0,0,0), (0,0,11), (0,0,0), (2,1,0), (2,1,26), (2,1,0):
        assert fn(x, y, value) == f(x, y, value)


def test_malloc():
    S = lltype.GcStruct("S", ('x',lltype.Signed))

    def f(n):
        s = lltype.malloc(S)
        s.x = n
        return s.x
    
    l3graph = l3ify(f, [int])
    def entry_point(x):
        value = l3interp.l3interpret(l3graph, [x], [], [])
        assert isinstance(value, l3interp.L3Integer)
        return value.intval

    assert entry_point(5) == f(5)

    fn = translate(entry_point, [int])

    assert fn(9) == f(9)

