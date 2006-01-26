from pypy.rpython.memory import gctransform
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.lltypesystem import lltype

def rtype_and_transform(func, inputtypes, transformcls):
    t = TranslationContext()
    t.buildannotator().build_types(func, inputtypes)
    t.buildrtyper().specialize(t)
    transformer = transformcls(t.graphs)
    transformer.transform()
    t.checkgraphs()
    return t

def test_simple():
    def f():
        return 1
    rtype_and_transform(f, [], gctransform.GCTransformer)

def test_fairly_simple():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c.x
    t = rtype_and_transform(f, [], gctransform.GCTransformer)

def test_return_gcpointer():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c
    t = rtype_and_transform(f, [], gctransform.GCTransformer)
    
def test_call_function():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c
    def g():
        return f().x
    t = rtype_and_transform(g, [], gctransform.GCTransformer)
    ggraph = graphof(t, g)
    for i, op in enumerate(ggraph.startblock.operations):
        if op.opname == "direct_call":
            break
    else:
        assert False, "direct_call not found!"
    assert ggraph.startblock.operations[i + 1].opname != 'push_alive'

def test_multiple_exits():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    T = lltype.GcStruct("T", ('y', lltype.Signed))
    def f(n):
        c = lltype.malloc(S)
        d = lltype.malloc(T)
        e = lltype.malloc(T)
        if n:
            x = d
        else:
            x = e
        return x
    t = rtype_and_transform(f, [int], gctransform.GCTransformer)
    fgraph = graphof(t, f)
    from pypy.translator.backendopt.ssa import SSI_to_SSA
    SSI_to_SSA(fgraph) # *cough*
    #t.view()
    pop_alive_count = 0
    for i, op in enumerate(fgraph.startblock.operations):
        if op.opname == "pop_alive":
            var, = op.args
            assert var.concretetype == lltype.Ptr(S)
            pop_alive_count += 1
    
    assert pop_alive_count == 1, "pop_alive not found!"
    for link in fgraph.startblock.exits:
        assert len(link.args) == 2
        ops = link.target.operations
        assert len(ops) == 1
        assert ops[0].opname == 'pop_alive'
        assert len(ops[0].args) == len(link.target.exits) == \
               len(link.target.exits[0].args) == 1
        dyingname = ops[0].args[0].name
        passedname = link.target.exits[0].args[0].name
        assert dyingname != passedname
    
def test_cleanup_vars_on_call():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f():
        return lltype.malloc(S)
    def g():
        s1 = f()
        s2 = f()
        s3 = f()
        return s1
    t = rtype_and_transform(g, [], gctransform.GCTransformer)
    ggraph = graphof(t, g)
    direct_calls = [op for op in ggraph.startblock.operations if op.opname == "direct_call"]
    assert len(direct_calls) == 3
    assert len(direct_calls[0].args) == 1
    assert direct_calls[1].args[1].value[0].args[0] == direct_calls[0].result
    assert [op.args[0] for op in direct_calls[2].args[1].value] == [direct_calls[0].result, direct_calls[1].result]

