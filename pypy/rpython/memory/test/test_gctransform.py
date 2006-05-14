from pypy.rpython.memory import gctransform
from pypy.objspace.flow.model import c_last_exception, Variable
from pypy.rpython.memory.gctransform import var_needsgc, var_ispyobj
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.c.exceptiontransform import ExceptionTransformer
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow.model import Variable
from pypy.annotation import model as annmodel
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy import conftest

import py

def checkblock(block, is_borrowed):
    if block.operations == ():
        # a return/exception block -- don't want to think about them
        # (even though the test passes for somewhat accidental reasons)
        return
    if block.isstartblock:
        refs_in = 0
    else:
        refs_in = len([v for v in block.inputargs if isinstance(v, Variable)
                                                  and var_needsgc(v)
                                                  and not is_borrowed(v)])
    push_alives = len([op for op in block.operations
                       if op.opname == 'gc_push_alive'])
    pyobj_push_alives = len([op for op in block.operations
                             if op.opname == 'gc_push_alive_pyobj'])

    # implicit_pyobj_pushalives included calls to things that return pyobject*
    implicit_pyobj_pushalives = len([op for op in block.operations
                                     if var_ispyobj(op.result)
                                     and op.opname not in ('getfield', 'getarrayitem', 'same_as')])
    nonpyobj_gc_returning_calls = len([op for op in block.operations
                                       if op.opname in ('direct_call', 'indirect_call')
                                       and var_needsgc(op.result)
                                       and not var_ispyobj(op.result)])
    
    pop_alives = len([op for op in block.operations
                      if op.opname == 'gc_pop_alive'])
    pyobj_pop_alives = len([op for op in block.operations
                            if op.opname == 'gc_pop_alive_pyobj'])
    if pop_alives == len(block.operations):
        # it's a block we inserted
        return
    for link in block.exits:
        assert block.exitswitch is not c_last_exception
        refs_out = 0
        for v2 in link.target.inputargs:
            if var_needsgc(v2) and not is_borrowed(v2):
                refs_out += 1
        pyobj_pushes = pyobj_push_alives + implicit_pyobj_pushalives
        nonpyobj_pushes = push_alives + nonpyobj_gc_returning_calls
        assert refs_in + pyobj_pushes + nonpyobj_pushes == pop_alives + pyobj_pop_alives + refs_out

def getops(graph):
    ops = {}
    for block in graph.iterblocks():
        for op in block.operations:
            ops.setdefault(op.opname, []).append(op)
    return ops

def rtype(func, inputtypes, specialize=True):
    t = TranslationContext()
    t.buildannotator().build_types(func, inputtypes)
    if specialize:
        t.buildrtyper().specialize(t)
    return t    

def rtype_and_transform(func, inputtypes, transformcls, specialize=True, check=True):
    t = rtype(func, inputtypes, specialize)
    etrafo = ExceptionTransformer(t)
    etrafo.transform_completely()
    transformer = transformcls(t)
    graphs_borrowed = {}
    for graph in t.graphs:
        graphs_borrowed[graph] = transformer.transform_graph(graph)
    if conftest.option.view:
        t.view()
    t.checkgraphs()
    if check:
        for graph, is_borrowed in graphs_borrowed.iteritems():
            for block in graph.iterblocks():
                checkblock(block, is_borrowed)
    return t, transformer

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
    t, transformer = rtype_and_transform(f, [], gctransform.GCTransformer)

def test_return_gcpointer():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c
    t, transformer = rtype_and_transform(f, [], gctransform.GCTransformer)
    
def test_call_function():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c
    def g():
        return f().x
    t, transformer = rtype_and_transform(g, [], gctransform.GCTransformer)
    ggraph = graphof(t, g)
    for i, op in enumerate(ggraph.startblock.operations):
        if op.opname == "direct_call":
            break
    else:
        assert False, "direct_call not found!"
    assert ggraph.startblock.operations[i + 1].opname != 'gc_push_alive'

def DONOTtest_multiple_exits():
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
    t, transformer = rtype_and_transform(f, [int], gctransform.GCTransformer)
    fgraph = graphof(t, f)
    from pypy.translator.backendopt.ssa import SSI_to_SSA
    SSI_to_SSA(fgraph) # *cough*
    #t.view()
    pop_alive_count = 0
    for i, op in enumerate(fgraph.startblock.operations):
        if op.opname == "gc_pop_alive":
            var, = op.args
            assert var.concretetype == lltype.Ptr(S)
            pop_alive_count += 1
    
    assert pop_alive_count == 1, "gc_pop_alive not found!"
    for link in fgraph.startblock.exits:
        assert len(link.args) == 2
        ops = link.target.operations
        assert len(ops) == 1
        assert ops[0].opname == 'gc_pop_alive'
        assert len(ops[0].args) == len(link.target.exits) == \
               len(link.target.exits[0].args) == 1
        dyingname = ops[0].args[0].name
        passedname = link.target.exits[0].args[0].name
        assert dyingname != passedname
    

def test_multiply_passed_var():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(x):
        if x:
            a = lltype.malloc(S)
            a.x = 1
            b = a
        else:
            a = lltype.malloc(S)
            a.x = 1
            b = lltype.malloc(S)
            b.x = 2
        return a.x + b.x
    t, transformer = rtype_and_transform(f, [int], gctransform.GCTransformer)

def test_pyobj():
    def f(x):
        if x:
            a = 1
        else:
            a = "1"
        return int(a)
    t, transformer = rtype_and_transform(f, [int], gctransform.GCTransformer)
    fgraph = graphof(t, f)
    gcops = [op for op in fgraph.startblock.exits[0].target.operations
                 if op.opname.startswith("gc_")]
    for op in gcops:
        assert op.opname.endswith("_pyobj")

def test_call_return_pyobj():
    def g(factory):
        return factory()
    def f(factory):
        g(factory)
    t, transformer = rtype_and_transform(f, [object], gctransform.GCTransformer)
    fgraph = graphof(t, f)
    ops = getops(fgraph)
    calls = ops['direct_call']
    for call in calls:
        if call.result.concretetype is not lltype.Bool: #RPyExceptionOccurred()
            assert var_ispyobj(call.result)

def test_getfield_pyobj():
    class S:
        pass
    def f(thing):
        s = S()
        s.x = thing
        return s.x
    t, transformer = rtype_and_transform(f, [object], gctransform.GCTransformer)
    fgraph = graphof(t, f)
    pyobj_getfields = 0
    pyobj_setfields = 0
    for b in fgraph.iterblocks():
        for op in b.operations:
            if op.opname == 'getfield' and var_ispyobj(op.result):
                pyobj_getfields += 1
            elif op.opname == 'setfield' and var_ispyobj(op.args[2]):
                pyobj_setfields += 1
    # although there's only one explicit getfield in the code, a
    # setfield on a pyobj must get the old value out and decref it
    assert pyobj_getfields >= 2
    assert pyobj_setfields >= 1

def test_pass_gc_pointer():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(s):
        s.x = 1
    def g():
        s = lltype.malloc(S)
        f(s)
        return s.x
    t, transformer = rtype_and_transform(g, [], gctransform.GCTransformer)
        
def DONOTtest_noconcretetype():
    def f():
        return [1][0]
    t, transformer = rtype_and_transform(f, [], gctransform.GCTransformer, specialize=False)
    fgraph = graphof(t, f)
    push_count = 0
    pop_count = 0
    for op in fgraph.startblock.operations:
        if op.opname == 'gc_push_alive_pyobj':
            push_count += 1
        elif op.opname == 'gc_pop_alive_pyobj':
            pop_count += 1
    assert push_count == 0 and pop_count == 1

# ____________________________________________________________________
# testing the protection magic and bare_setfield

def protect(obj): RaiseNameError
def unprotect(obj): RaiseNameError

class Entry(ExtRegistryEntry):
    _about_ = protect
    s_result_annotation = None
    def specialize_call(self, hop):
        hop.genop('gc_protect', hop.inputargs(hop.args_r[0]))

class Entry(ExtRegistryEntry):
    _about_ = unprotect
    s_result_annotation = None
    def specialize_call(self, hop):
        hop.genop('gc_unprotect', hop.inputargs(hop.args_r[0]))

def test_protect_unprotect():
    def p():    protect('this is an object')
    def u():    unprotect('this is an object')

    rgc = gctransform.RefcountingGCTransformer
    bgc = gctransform.BoehmGCTransformer
    expected = [1, 1, 0, 0]
    gcs = [rgc, rgc, bgc, bgc]
    fs = [p, u, p, u]
    for ex, f, gc in zip(expected, fs, gcs):
        t, transformer = rtype_and_transform(f, [], gc, check=False)
        ops = getops(graphof(t, f))
        assert len(ops.get('direct_call', [])) == ex

def generic_op(*args): RaiseNameError

class Entry(ExtRegistryEntry):
    _about_ = generic_op
    s_result_annotation = None
    def specialize_call(self, hop):
        args = hop.inputargs(*hop.args_r)
        args.pop(0)
        op = hop.args_s[0].const
        hop.genop(op, args)

def test_bare_setfield():
    class A:
        def __init__(self, obj): self.x = obj
    def f(v):
        inst = A(v)
        generic_op('setfield', inst, 'x', v)
        generic_op('bare_setfield', inst, 'x', v)

    rgc = gctransform.RefcountingGCTransformer
    bgc = gctransform.BoehmGCTransformer
    # should not influence PyObject at all
    for gc in rgc, bgc:
        t, transformer = rtype_and_transform(f, [object], gc, check=False)
        ops = getops(graphof(t, f))
        assert len(ops.get('getfield', [])) == 2

def DONOTtest_protect_unprotect_no_exception_block():
    def p():    protect('this is an object')
    def u():    unprotect('this is an object')

    gc = gctransform.RefcountingGCTransformer
    for f in p, u:
        t, transformer = rtype_and_transform(f, [], gc, check=False)
        ops = getops(graphof(t, f))
        for op in ops.get('direct_call', []):
            assert op.cleanup is None or op.cleanup == ((), ())

# end of protection tests

def test_except_block():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(a, n):
        if n == 0:
            raise ValueError
        a.x = 1
        return a
    def g(n):
        a = lltype.malloc(S)
        try:
            return f(a, n).x
        except ValueError:
            return 0
    t, transformer = rtype_and_transform(g, [int], gctransform.GCTransformer)

def test_except_block2():
    # the difference here is that f() returns Void, not a GcStruct
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(a, n):
        if n == 0:
            raise ValueError
        a.x = 1
    def g(n):
        a = lltype.malloc(S)
        try:
            f(a, n)
            return a.x
        except ValueError:
            return 0
    t, transformer = rtype_and_transform(g, [int], gctransform.GCTransformer)
    
def test_no_livevars_with_exception():
    def g():
        raise TypeError
    def f():
        try:
            g()
        except TypeError:
            return 0
        return 1
    t, transformer = rtype_and_transform(f, [], gctransform.GCTransformer)

def test_refcounting_incref_simple():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c.x
    t, transformer = rtype_and_transform(f, [], gctransform.RefcountingGCTransformer, check=False)
    ops = getops(graphof(t, f))
    assert ops['direct_call'] >= 4


def test_boehm_simple():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c.x
    t, transformer = rtype_and_transform(
        f, [], gctransform.BoehmGCTransformer, check=False)
    ops = getops(graphof(t, f))
    assert len(ops.get('direct_call', [])) <= 1
    gcs = [k for k in ops if k.startswith('gc')]
    assert len(gcs) == 0


  
# ______________________________________________________________________
# test write barrier placement

def test_simple_barrier():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    T = lltype.GcStruct("T", ('s', lltype.Ptr(S)))
    def f():
        s1 = lltype.malloc(S)
        s1.x = 1
        s2 = lltype.malloc(S)
        s2.x = 2
        t = lltype.malloc(T)
        t.s = s1
        t.s = s2
        return t
    t, transformer = rtype_and_transform(f, [], gctransform.RefcountingGCTransformer, check=False)
    graph = graphof(t, f)
    ops = getops(graph)
    assert len(ops['getfield']) == 5
    assert len(ops['setfield']) == 4

def test_arraybarrier():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    A = lltype.GcArray(lltype.Ptr(S))
    def f():
        s1 = lltype.malloc(S)
        s1.x = 1
        s2 = lltype.malloc(S)
        s2.x = 2
        a = lltype.malloc(A, 1)
        a[0] = s1
        a[0] = s2
    t, transformer = rtype_and_transform(f, [], gctransform.RefcountingGCTransformer, check=False)
    graph = graphof(t, f)
    ops = getops(graph)
    assert len(ops['getarrayitem']) == 2
    assert len(ops['setarrayitem']) == 2
    assert len(ops['setfield']) == 2


# ----------------------------------------------------------------------
# test deallocators

def make_deallocator(TYPE,
                     attr="static_deallocation_funcptr_for_type",
                     cls=gctransform.RefcountingGCTransformer):
    def f():
        pass
    t = TranslationContext()
    t.buildannotator().build_types(f, [])
    t.buildrtyper().specialize(t)
    transformer = cls(t)
    fptr = getattr(transformer, attr)(TYPE)
    transformer.finish()
    if conftest.option.view:
        t.view()
    if fptr:
        return fptr._obj.graph, t
    else:
        return None, t

def make_boehm_finalizer(TYPE):
    return make_deallocator(TYPE, attr="finalizer_funcptr_for_type",
                            cls=gctransform.BoehmGCTransformer)

def test_deallocator_simple():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    dgraph, t = make_deallocator(S)
    ops = []
    for block in dgraph.iterblocks():
        ops.extend([op for op in block.operations if op.opname != 'same_as']) # XXX
    assert len(ops) == 1
    op = ops[0]
    assert op.opname == 'gc_free'

def test_deallocator_less_simple():
    TPtr = lltype.Ptr(lltype.GcStruct("T", ('a', lltype.Signed)))
    S = lltype.GcStruct(
        "S",
        ('x', lltype.Signed),
        ('y', TPtr),
        ('z', TPtr),
        )
    dgraph, t = make_deallocator(S)
    ops = getops(dgraph)
    assert len(ops['direct_call']) == 2
    assert len(ops['getfield']) == 2
    assert len(ops['gc_free']) == 1

def test_deallocator_array():
    TPtr = lltype.Ptr(lltype.GcStruct("T", ('a', lltype.Signed)))
    GcA = lltype.GcArray(('x', TPtr), ('y', TPtr))
    A = lltype.Array(('x', TPtr), ('y', TPtr))
    APtr = lltype.Ptr(GcA)
    S = lltype.GcStruct('S', ('t', TPtr), ('x', lltype.Signed), ('aptr', APtr),
                             ('rest', A))
    dgraph, t = make_deallocator(S)
    ops = getops(dgraph)
    assert len(ops['direct_call']) == 4
    assert len(ops['getfield']) == 4
    assert len(ops['getarraysubstruct']) == 1
    assert len(ops['gc_free']) == 1

def test_deallocator_with_destructor():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(s):
        s.x = 1
    def type_info_S(p):
        return lltype.getRuntimeTypeInfo(S)
    qp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Ptr(lltype.RuntimeTypeInfo)),
                            "type_info_S", 
                            _callable=type_info_S)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void), 
                            "destructor_funcptr", 
                            _callable=f)
    pinf = lltype.attachRuntimeTypeInfo(S, qp, destrptr=dp)
    graph, t = make_deallocator(S)

def test_caching_dynamic_deallocator():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    S1 = lltype.GcStruct("S1", ('s', S), ('y', lltype.Signed))
    T = lltype.GcStruct("T", ('x', lltype.Signed))
    def f_S(s):
        s.x = 1
    def f_S1(s1):
        s1.s.x = 1
        s1.y = 2
    def f_T(s):
        s.x = 1
    def type_info_S(p):
        return lltype.getRuntimeTypeInfo(S)
    def type_info_T(p):
        return lltype.getRuntimeTypeInfo(T)
    qp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Ptr(lltype.RuntimeTypeInfo)),
                            "type_info_S", 
                            _callable=type_info_S)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void), 
                            "destructor_funcptr", 
                            _callable=f_S)
    pinf = lltype.attachRuntimeTypeInfo(S, qp, destrptr=dp)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void), 
                            "destructor_funcptr", 
                            _callable=f_S1)
    pinf = lltype.attachRuntimeTypeInfo(S1, qp, destrptr=dp)
    qp = lltype.functionptr(lltype.FuncType([lltype.Ptr(T)],
                                            lltype.Ptr(lltype.RuntimeTypeInfo)),
                            "type_info_S", 
                            _callable=type_info_T)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(T)],
                                            lltype.Void), 
                            "destructor_funcptr", 
                            _callable=f_T)
    pinf = lltype.attachRuntimeTypeInfo(T, qp, destrptr=dp)
    def f():
        pass
    t = TranslationContext()
    t.buildannotator().build_types(f, [])
    t.buildrtyper().specialize(t)
    transformer = gctransform.RefcountingGCTransformer(t)
    p_S = transformer.dynamic_deallocation_funcptr_for_type(S)
    p_S1 = transformer.dynamic_deallocation_funcptr_for_type(S1)
    p_T = transformer.dynamic_deallocation_funcptr_for_type(T)
    assert p_S is not p_T
    assert p_S is p_S1

def test_dynamic_deallocator():
    class A(object):
        pass
    class B(A):
        pass
    def f(x):
        a = A()
        a.x = 1
        b = B()
        b.x = 2
        b.y = 3
        if x:
            c = a
        else:
            c = b
        return c.x
    t, transformer = rtype_and_transform(
        f, [int], gctransform.RefcountingGCTransformer, check=False)
    fgraph = graphof(t, f)
    TYPE = fgraph.startblock.operations[0].result.concretetype.TO
    p = transformer.dynamic_deallocation_funcptr_for_type(TYPE)
    t.rtyper.specialize_more_blocks() 

def test_recursive_structure():
    F = lltype.GcForwardReference()
    S = lltype.GcStruct('abc', ('x', lltype.Ptr(F)))
    F.become(S)
    def f():
        s1 = lltype.malloc(S)
        s2 = lltype.malloc(S)
        s1.x = s2
    t, transformer = rtype_and_transform(
        f, [], gctransform.RefcountingGCTransformer, check=False)

def test_dont_decref_nongc_pointers():
    S = lltype.GcStruct('S',
                        ('x', lltype.Ptr(lltype.Struct('T', ('x', lltype.Signed)))),
                        ('y', lltype.Ptr(lltype.GcStruct('Y', ('x', lltype.Signed))))
                        )
    def f():
        pass
    graph, t = make_deallocator(S)
    ops = getops(graph)
    assert len(ops['direct_call']) == 1

def test_boehm_finalizer_simple():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    f, t = make_boehm_finalizer(S)
    assert f is None

def test_boehm_finalizer_pyobj():
    S = lltype.GcStruct("S", ('x', lltype.Ptr(lltype.PyObject)))
    f, t = make_boehm_finalizer(S)
    assert f is not None

def test_boehm_finalizer___del__():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(s):
        s.x = 1
    def type_info_S(p):
        return lltype.getRuntimeTypeInfo(S)
    qp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Ptr(lltype.RuntimeTypeInfo)),
                            "type_info_S", 
                            _callable=type_info_S)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void), 
                            "destructor_funcptr", 
                            _callable=f)
    pinf = lltype.attachRuntimeTypeInfo(S, qp, destrptr=dp)
    f, t = make_boehm_finalizer(S)
    assert f is not None

def test_boehm_finalizer_nomix___del___and_pyobj():
    S = lltype.GcStruct("S", ('x', lltype.Signed), ('y', lltype.Ptr(lltype.PyObject)))
    def f(s):
        s.x = 1
    def type_info_S(p):
        return lltype.getRuntimeTypeInfo(S)
    qp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Ptr(lltype.RuntimeTypeInfo)),
                            "type_info_S", 
                            _callable=type_info_S)
    dp = lltype.functionptr(lltype.FuncType([lltype.Ptr(S)],
                                            lltype.Void), 
                            "destructor_funcptr", 
                            _callable=f)
    pinf = lltype.attachRuntimeTypeInfo(S, qp, destrptr=dp)
    py.test.raises(Exception, "make_boehm_finalizer(S)")

# ______________________________________________________________________
# test statistics

def test_count_vars_simple():
    S = lltype.GcStruct('abc', ('x', lltype.Signed))
    def f():
        s1 = lltype.malloc(S)
        s2 = lltype.malloc(S)
        s1.x = 1
        s2.x = 2
        return s1.x + s2.x
    t = rtype(f, [])
    assert gctransform.relevant_gcvars_graph(graphof(t, f)) == [0, 1]

def test_count_vars_big():
    from pypy.translator.goal.targetrpystonex import make_target_definition
    from pypy.translator.backendopt.all import backend_optimizations
    entrypoint, _, _ = make_target_definition(10)
    t = rtype(entrypoint, [int])
    backend_optimizations(t)
    # does not crash
    rel = gctransform.relevant_gcvars(t)
    print rel
    print sum(rel) / float(len(rel)), max(rel), min(rel)

    rel = gctransform.relevant_gcvars(t, gctransform.filter_for_nongcptr)
    print rel
    print sum(rel) / float(len(rel)), max(rel), min(rel)

# ______________________________________________________________________
# tests for FrameworkGCTransformer

def test_framework_simple():
    def g(x):
        return x + 1
    class A(object):
        pass
    def entrypoint(argv):
        a = A()
        a.b = g(1)
        return str(a.b)

    from pypy.rpython.llinterp import LLInterpreter
    from pypy.translator.c.genc import CStandaloneBuilder
    from pypy.translator.c import gc
    from pypy.annotation.listdef import s_list_of_strings
    
    t = rtype(entrypoint, [s_list_of_strings])
    cbuild = CStandaloneBuilder(t, entrypoint, gc.FrameworkGcPolicy)
    db = cbuild.generate_graphs_for_llinterp()
    entrypointptr = cbuild.getentrypointptr()
    entrygraph = entrypointptr._obj.graph

    r_list_of_strings = t.rtyper.getrepr(s_list_of_strings)
    ll_argv = r_list_of_strings.convert_const([])

    llinterp = LLInterpreter(t.rtyper)
    
    # FIIIIISH
    setupgraph = db.gctransformer.frameworkgc_setup_ptr.value._obj.graph
    llinterp.eval_graph(setupgraph, [])

    res = llinterp.eval_graph(entrygraph, [ll_argv])

    assert ''.join(res.chars) == "2"
