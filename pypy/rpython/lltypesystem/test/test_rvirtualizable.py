import py
from pypy.objspace.flow.model import summary
from pypy.rlib.jit import hint
from pypy.rpython.lltypesystem import lltype, rclass
from pypy.rpython.test.test_llinterp import interpret, get_interpreter
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.error import TyperError

class V(object):
    _virtualizable_ = True

    def __init__(self, v):
        self.v = v

def test_simple():
    def f(v):
        vinst = V(v)
        return vinst, vinst.v
    res = interpret(f, [42])
    assert res.item1 == 42
    res = lltype.normalizeptr(res.item0)
    assert res.inst_v == 42
    assert not res.vable_access
    LLV = lltype.typeOf(res)
    ACCESS = lltype.typeOf(res.vable_access).TO
    assert ACCESS.get_inst_v == lltype.Ptr(lltype.FuncType([LLV],
                                                           lltype.Signed))
    assert ACCESS.set_inst_v == lltype.Ptr(lltype.FuncType([LLV, lltype.Signed],
                                                           lltype.Void))    

def test_get_accessor():

    G = lltype.FuncType([rclass.OBJECTPTR], lltype.Void)

    witness = []
    
    def getv(vinst):
        value = vinst.inst_v
        witness.append(value)
        return value

    def g(vobj):
        vobj = lltype.normalizeptr(vobj)
        LLV = lltype.typeOf(vobj).TO
        ACCESS = LLV.vable_access.TO
        access = lltype.malloc(ACCESS, immortal=True)
        access.get_inst_v = lltype.functionptr(ACCESS.get_inst_v.TO,
                                               'getv', _callable=getv)
        vobj.vable_access = access
        
    gptr = lltype.functionptr(G, 'g', _callable=g)
    
    def f(v):
        vinst = V(v)
        vobj = cast_instance_to_base_ptr(vinst)
        gptr(vobj)
        x = vinst.v
        return x
    res = interpret(f, [42])
    assert res == 42

    assert witness == [42]

def test_set_accessor():

    G = lltype.FuncType([rclass.OBJECTPTR], lltype.Void)

    witness = []
    
    def setv(vinst, val):
        witness.append(val)
        vinst.inst_v = val

    def g(vobj):
        vobj = lltype.normalizeptr(vobj)
        LLV = lltype.typeOf(vobj).TO
        ACCESS = LLV.vable_access.TO
        access = lltype.malloc(ACCESS, immortal=True)
        access.set_inst_v = lltype.functionptr(ACCESS.set_inst_v.TO,
                                               'setv', _callable=setv)
        vobj.vable_access = access
        
    gptr = lltype.functionptr(G, 'g', _callable=g)
    
    def f(v):
        vinst = V(v)
        vobj = cast_instance_to_base_ptr(vinst)
        gptr(vobj)
        vinst.v = 33
    res = interpret(f, [42])

    assert witness == [33]

class B(object):
    _virtualizable_ = True

    x = "XX"
    
    def __init__(self, v0):
        self.v0 = v0

class C(B):

    x = "XXX"
    
    def __init__(self, v0, v1):
        B.__init__(self, v0)
        self.v1 = v1


def test_get_accessor_inheritance():

    G = lltype.FuncType([rclass.OBJECTPTR], lltype.Void)

    witness = []
    
    def getv0(vinst):
        value = vinst.inst_v0
        witness.append(value)
        return value

    def getv1(vinst):
        value = lltype.normalizeptr(vinst).inst_v1
        witness.append(value)
        return value    

    def g(vobj):
        vobj = lltype.normalizeptr(vobj)
        LLV = lltype.typeOf(vobj).TO
        ACCESS = LLV.ACCESS
        access = lltype.malloc(ACCESS, immortal=True)
        fp = lltype.functionptr(ACCESS.parent.get_inst_v0.TO, 'getv0',
                                _callable=getv0)        
        access.parent.get_inst_v0= fp
                                     
        access.get_inst_v1 = lltype.functionptr(ACCESS.get_inst_v1.TO,
                                               'getv1', _callable=getv1)
        vobj.super.vable_access = access.parent
        
    gptr = lltype.functionptr(G, 'g', _callable=g)
    
    def f(v0, v1):
        B(0)
        vinst = C(v0, v1)
        vobj = cast_instance_to_base_ptr(vinst)
        gptr(vobj)
        x = vinst.v0
        y = vinst.v1
        vinst.x
        return x+y+len(vinst.x)
    res = interpret(f, [18, 21])
    assert res == 42

    assert witness == [18, 21]

class A(object):
    def __init__(self, v):
        self.v = v

class AA(A):
    _virtualizable_ = True

    def __init__(self, vv):
        self.vv = vv

def test_parent_has_attrs_failure():
    def f():
        A(1)
        AA(3)

    py.test.raises(TyperError, interpret, f, [])

def test_read_not_redirected_field():
    class V(object):
        _virtualizable_ = True

        def __init__(self, v):
            self.v = v
    def f(v):
        vinst = V(v)
        return vinst, vinst.v, vinst.__class__
    res = interpret(f, [42])
    assert res.item1 == 42
    

def test_void_fields():
    class F(object):
        def _freeze_(self):
            return True

    f = F()
    
    class V(object):
        _virtualizable_ = True

        def __init__(self, v):
            self.v = v
            self.f = f
    def f(v):
        vinst = V(v)
        return vinst, vinst.v, vinst.f
    res = interpret(f, [42])
    assert res.item1 == 42
    

def test_access_directly():
    def g(b):
        return b.v0

    def f(n):
        b = B(n)
        b = hint(b, access_directly=True)
        return g(b)

    interp, graph = get_interpreter(f, [23])
    g_graph = interp.typer.annotator.translator._graphof(g)
    assert summary(g_graph) == {'getfield': 1}

    res = interp.eval_graph(graph, [23])
    assert res == 23


def test_access_directly_specialized():
    def g(b):
        return b.v0

    def f(n):
        b = B(n)
        x = g(b)
        y = g(hint(b, access_directly=True))
        return x + y

    interp, graph = get_interpreter(f, [23])
    desc = interp.typer.annotator.bookkeeper.getdesc(g)
    g_graphs = desc._cache.values()
    assert len(g_graphs) == 2
    summaries = map(summary, g_graphs)
    summaries.sort()
    assert summaries == [{'direct_call': 1},
                         {'getfield': 1}]

    res = interp.eval_graph(graph, [23])
    assert res == 46


def test_access_directly_escape():
    class Global:
        pass
    glob = Global()

    def g(b):
        glob.b = b

    def h(b):
        return b.v0

    def f(n):
        b = B(n)
        g(b)
        g(hint(b, access_directly=True))
        return h(glob.b)

    interp, graph = get_interpreter(f, [23])
    desc = interp.typer.annotator.bookkeeper.getdesc(g)
    g_graphs = desc._cache.values()
    assert len(g_graphs) == 2
    summaries = map(summary, g_graphs)
    summaries.sort()
    assert summaries == [{'setfield': 1},
                         {'setfield': 1}]
    h_graph = interp.typer.annotator.translator._graphof(h)
    assert summary(h_graph) == {'direct_call': 1}

    res = interp.eval_graph(graph, [23])
    assert res == 23


def test_access_directly_method():
    class A(B):
        def meth1(self, x):
            return self.g(x+1)

        def g(self, y):
            return self.v0 * y

    def f(n):
        a = A(n)
        a = hint(a, access_directly=True)
        return a.meth1(100)

    interp, graph = get_interpreter(f, [23])
    g_graph = interp.typer.annotator.translator._graphof(A.g.im_func)
    assert summary(g_graph) == {'getfield': 1, 'int_mul': 1}

    res = interp.eval_graph(graph, [23])
    assert res == 2323
