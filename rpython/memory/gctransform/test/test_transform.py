from rpython.memory.gctransform.transform import BaseGCTransformer
from rpython.flowspace.model import Variable
from rpython.translator.backendopt.support import var_needsgc
from rpython.translator.translator import TranslationContext, graphof
from rpython.translator.exceptiontransform import ExceptionTransformer
from rpython.rtyper.lltypesystem import lltype
from rpython.conftest import option
from rpython.rtyper.rtyper import llinterp_backend

class LLInterpedTranformerTests:

    def llinterpreter_for_transformed_graph(self, f):
        from rpython.rtyper.llinterp import LLInterpreter
        from rpython.translator.c.genc import CStandaloneBuilder
        from rpython.translator.c import gc
        from rpython.annotation.listdef import s_list_of_strings

        t = rtype(f, [s_list_of_strings])
        # XXX we shouldn't need an actual gcpolicy here.
        cbuild = CStandaloneBuilder(t, f, t.config, gcpolicy=self.gcpolicy)
        cbuild.make_entrypoint_wrapper = False
        cbuild.build_database()
        graph = cbuild.getentrypointptr()._obj.graph
        llinterp = LLInterpreter(t.rtyper)
        if option.view:
            t.view()
        return llinterp, graph


    def test_simple(self):
        from rpython.annotator.model import SomeInteger

        class C:
            pass
        c = C()
        c.x = 1
        def g(x):
            if x:
                return c
            else:
                d = C()
                d.x = 2
                return d
        def f(argv):
            x = int(argv[1])
            return g(x).x

        llinterp, graph = self.llinterpreter_for_transformed_graph(f)

        res = llinterp.eval_entry_point(graph, ["0"])
        assert res == f(["", "0"])
        res = llinterp.eval_entry_point(graph, ["1"])
        assert res == f(["", "1"])

    def test_simple_varsize(self):
        from rpython.annotator.model import SomeInteger

        def f(argv):
            x = int(argv[1])
            r = []
            for i in range(x):
                if i % 2:
                    r.append(x)
            return len(r)


        llinterp, graph = self.llinterpreter_for_transformed_graph(f)

        res = llinterp.eval_entry_point(graph, ["0"])
        assert res == f(["", "0"])
        res = llinterp.eval_entry_point(graph, ["10"])
        assert res == f(["", "10"])

    def test_str(self):
        from rpython.annotator.model import SomeBool

        def f(argv):
            flag = int(argv[1])
            if flag:
                x = 'a'
            else:
                x = 'brrrrrrr'
            return len(x + 'a')


        llinterp, graph = self.llinterpreter_for_transformed_graph(f)

        res = llinterp.eval_entry_point(graph, ["1"])
        assert res == f(["", "1"])
        res = llinterp.eval_entry_point(graph, ["0"])
        assert res == f(["", "0"])

class _TestGCTransformer(BaseGCTransformer):

    def push_alive_nopyobj(self, var, llops):
        llops.genop("gc_push_alive", [var])

    def pop_alive_nopyobj(self, var, llops):
        llops.genop("gc_pop_alive", [var])


def checkblock(block, is_borrowed, is_start_block):
    if block.operations == ():
        # a return/exception block -- don't want to think about them
        # (even though the test passes for somewhat accidental reasons)
        return
    if is_start_block:
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
    assert not block.canraise
    for link in block.exits:
        refs_out = 0
        for v2 in link.target.inputargs:
            if var_needsgc(v2) and not is_borrowed(v2):
                refs_out += 1
        pyobj_pushes = pyobj_push_alives + implicit_pyobj_pushalives
        nonpyobj_pushes = push_alives + nonpyobj_gc_returning_calls
        assert refs_in + pyobj_pushes + nonpyobj_pushes == pop_alives + pyobj_pop_alives + refs_out

def rtype(func, inputtypes, specialize=True):
    t = TranslationContext()
    t.buildannotator().build_types(func, inputtypes)
    rtyper = t.buildrtyper()
    rtyper.backend = llinterp_backend
    if specialize:
        rtyper.specialize()
    if option.view:
        t.view()
    return t    

def rtype_and_transform(func, inputtypes, transformcls, specialize=True, check=True):
    t = rtype(func, inputtypes, specialize)
    transformer = transformcls(t)
    etrafo = ExceptionTransformer(t)
    etrafo.transform_completely()
    graphs_borrowed = {}
    for graph in t.graphs:
        graphs_borrowed[graph] = transformer.transform_graph(graph)
    if option.view:
        t.view()
    t.checkgraphs()
    if check:
        for graph, is_borrowed in graphs_borrowed.iteritems():
            for block in graph.iterblocks():
                checkblock(block, is_borrowed, block is graph.startblock)
    return t, transformer

def getops(graph):
    ops = {}
    for block in graph.iterblocks():
        for op in block.operations:
            ops.setdefault(op.opname, []).append(op)
    return ops

def test_simple():
    def f():
        return 1
    rtype_and_transform(f, [], _TestGCTransformer)

def test_fairly_simple():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c.x
    t, transformer = rtype_and_transform(f, [], _TestGCTransformer)

def test_return_gcpointer():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c
    t, transformer = rtype_and_transform(f, [], _TestGCTransformer)
    
def test_call_function():
    class C:
        pass
    def f():
        c = C()
        c.x = 1
        return c
    def g():
        return f().x
    t, transformer = rtype_and_transform(g, [], _TestGCTransformer)
    ggraph = graphof(t, g)
    for i, op in enumerate(ggraph.startblock.operations):
        if op.opname == "direct_call":
            break
    else:
        assert False, "direct_call not found!"
    assert ggraph.startblock.operations[i + 1].opname != 'gc_push_alive'


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
    t, transformer = rtype_and_transform(f, [int], _TestGCTransformer)

def test_pyobj():
    def f(x):
        if x:
            a = 1
        else:
            a = "1"
        return int(a)
    t, transformer = rtype_and_transform(f, [int], _TestGCTransformer)
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
    t, transformer = rtype_and_transform(f, [object], _TestGCTransformer)
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
    t, transformer = rtype_and_transform(f, [object], _TestGCTransformer)
    fgraph = graphof(t, f)
    pyobj_getfields = 0
    pyobj_setfields = 0
    for b in fgraph.iterblocks():
        for op in b.operations:
            if op.opname == 'getfield' and var_ispyobj(op.result):
                pyobj_getfields += 1
            elif op.opname == 'bare_setfield' and var_ispyobj(op.args[2]):
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
    t, transformer = rtype_and_transform(g, [], _TestGCTransformer)

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
    t, transformer = rtype_and_transform(g, [int], _TestGCTransformer)

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
    t, transformer = rtype_and_transform(g, [int], _TestGCTransformer)
    
def test_no_livevars_with_exception():
    def g():
        raise TypeError
    def f():
        try:
            g()
        except TypeError:
            return 0
        return 1
    t, transformer = rtype_and_transform(f, [], _TestGCTransformer)

def test_bare_setfield():
    from rpython.rtyper.lltypesystem.lloperation import llop
    class A:
        def __init__(self, obj): self.x = obj
    def f(v):
        inst = A(v)
        llop.setfield(lltype.Void, inst, 'x', v)
        llop.bare_setfield(lltype.Void, inst, 'x', v)

    t, transformer = rtype_and_transform(f, [object], _TestGCTransformer,
                                         check=False)
    ops = getops(graphof(t, f))
    assert len(ops.get('getfield', [])) == 1
