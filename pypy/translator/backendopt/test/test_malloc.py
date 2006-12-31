import py
from pypy.translator.backendopt.malloc import LLTypeMallocRemover
from pypy.translator.backendopt.inline import inline_function
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator import simplify
from pypy.objspace.flow.model import checkgraph, flatten, Block, mkentrymap
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib import objectmodel
from pypy.conftest import option


def check_malloc_removed(graph):
    remover = LLTypeMallocRemover()
    checkgraph(graph)
    count1 = count2 = 0
    for node in flatten(graph):
        if isinstance(node, Block):
            for op in node.operations:
                if op.opname == 'malloc':
                    S = op.args[0].value
                    if not remover.union_wrapper(S):   # union wrappers are fine
                        count1 += 1
                if op.opname in ('direct_call', 'indirect_call'):
                    count2 += 1
    assert count1 == 0   # number of mallocs left
    assert count2 == 0   # number of calls left

def check(fn, signature, args, expected_result, must_be_removed=True):
    remover = LLTypeMallocRemover()
    t = TranslationContext()
    t.buildannotator().build_types(fn, signature)
    t.buildrtyper().specialize()
    graph = graphof(t, fn)
    if option.view:
        t.view()
    # to detect missing keepalives and broken intermediate graphs,
    # we do the loop ourselves instead of calling remove_simple_mallocs()
    while True:
        progress = remover.remove_mallocs_once(graph)
        simplify.transform_dead_op_vars_in_blocks(list(graph.iterblocks()))
        if progress and option.view:
            t.view()
        if expected_result is not Ellipsis:
            interp = LLInterpreter(t.rtyper)
            res = interp.eval_graph(graph, args)
            assert res == expected_result
        if not progress:
            break
    if must_be_removed:
        check_malloc_removed(graph)
    return graph


def test_fn1():
    def fn1(x, y):
        if x > 0:
            t = x+y, x-y
        else:
            t = x-y, x+y
        s, d = t
        return s*d
    check(fn1, [int, int], [15, 10], 125)

def test_fn2():
    class T:
        pass
    def fn2(x, y):
        t = T()
        t.x = x
        t.y = y
        if x > 0:
            return t.x + t.y
        else:
            return t.x - t.y
    check(fn2, [int, int], [-6, 7], -13)

def test_fn3():
    def fn3(x):
        a, ((b, c), d, e) = x+1, ((x+2, x+3), x+4, x+5)
        return a+b+c+d+e
    check(fn3, [int], [10], 65)

def test_fn4():
    class A:
        pass
    class B(A):
        pass
    def fn4(i):
        a = A()
        b = B()
        a.b = b
        b.i = i
        return a.b.i
    check(fn4, [int], [42], 42)

def test_fn5():
    class A:
        attr = 666
    class B(A):
        attr = 42
    def fn5():
        b = B()
        return b.attr
    check(fn5, [], [], 42)

def test_aliasing():
    class A:
        pass
    def fn6(n):
        a1 = A()
        a1.x = 5
        a2 = A()
        a2.x = 6
        if n > 0:
            a = a1
        else:
            a = a2
        a.x = 12
        return a1.x
    check(fn6, [int], [1], 12, must_be_removed=False)

def test_with_keepalive():
    from pypy.rlib.objectmodel import keepalive_until_here
    def fn1(x, y):
        if x > 0:
            t = x+y, x-y
        else:
            t = x-y, x+y
        s, d = t
        keepalive_until_here(t)
        return s*d
    check(fn1, [int, int], [15, 10], 125)

def test_dont_remove_with__del__():
    import os
    delcalls = [0]
    class A(object):
        nextid = 0
        def __init__(self):
            self.id = self.nextid
            self.nextid += 1

        def __del__(self):
            delcalls[0] += 1
            os.write(1, "__del__\n")

    def f(x=int):
        a = A()
        i = 0
        while i < x:
            a = A()
            os.write(1, str(delcalls[0]) + "\n")
            i += 1
        return 1
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backend_optimizations(t)
    op = graph.startblock.exits[0].target.exits[1].target.operations[0]
    assert op.opname == "malloc"

def test_add_keepalives():
    class A:
        pass
    SMALL = lltype.Struct('SMALL', ('x', lltype.Signed))
    BIG = lltype.GcStruct('BIG', ('z', lltype.Signed), ('s', SMALL))
    def fn7(i):
        big = lltype.malloc(BIG)
        a = A()
        a.big = big
        a.small = big.s
        a.small.x = 0
        while i > 0:
            a.small.x += i
            i -= 1
        return a.small.x
    check(fn7, [int], [10], 55, must_be_removed=False)

def test_getsubstruct():
    SMALL = lltype.Struct('SMALL', ('x', lltype.Signed))
    BIG = lltype.GcStruct('BIG', ('z', lltype.Signed), ('s', SMALL))

    def fn(n1, n2):
        b = lltype.malloc(BIG)
        b.z = n1
        b.s.x = n2
        return b.z - b.s.x

    check(fn, [int, int], [100, 58], 42)

def test_fixedsizearray():
    A = lltype.FixedSizeArray(lltype.Signed, 3)
    S = lltype.GcStruct('S', ('a', A))

    def fn(n1, n2):
        s = lltype.malloc(S)
        a = s.a
        a[0] = n1
        a[2] = n2
        return a[0]-a[2]

    check(fn, [int, int], [100, 42], 58)

def test_wrapper_cannot_be_removed():
    SMALL = lltype.OpaqueType('SMALL')
    BIG = lltype.GcStruct('BIG', ('z', lltype.Signed), ('s', SMALL))

    def g(small):
        return -1
    def fn():
        b = lltype.malloc(BIG)
        g(b.s)

    check(fn, [], [], None, must_be_removed=False)

def test_direct_fieldptr():
    S = lltype.GcStruct('S', ('x', lltype.Signed))

    def fn():
        s = lltype.malloc(S)
        s.x = 11
        p = lltype.direct_fieldptr(s, 'x')
        return p[0]

    check(fn, [], [], 11)

def test_direct_fieldptr_2():
    T = lltype.GcStruct('T', ('z', lltype.Signed))
    S = lltype.GcStruct('S', ('t', T),
                             ('x', lltype.Signed),
                             ('y', lltype.Signed))
    def fn():
        s = lltype.malloc(S)
        s.x = 10
        s.t.z = 1
        px = lltype.direct_fieldptr(s, 'x')
        py = lltype.direct_fieldptr(s, 'y')
        pz = lltype.direct_fieldptr(s.t, 'z')
        py[0] = 31
        return px[0] + s.y + pz[0]

    check(fn, [], [], 42)

def test_getarraysubstruct():
    U = lltype.Struct('U', ('n', lltype.Signed))
    for length in [1, 2]:
        S = lltype.GcStruct('S', ('a', lltype.FixedSizeArray(U, length)))
        for index in range(length):

            def fn():
                s = lltype.malloc(S)
                s.a[index].n = 12
                return s.a[index].n
            check(fn, [], [], 12)

def test_ptr_nonzero():
    S = lltype.GcStruct('S')
    def fn():
        s = lltype.malloc(S)
        return bool(s)
    check(fn, [], [], True)

def test_substruct_not_accessed():
    SMALL = lltype.Struct('SMALL', ('x', lltype.Signed))
    BIG = lltype.GcStruct('BIG', ('z', lltype.Signed), ('s', SMALL))
    def fn():
        x = lltype.malloc(BIG)
        while x.z < 10:    # makes several blocks
            x.z += 3
        return x.z
    check(fn, [], [], 12)

def test_union():
    UNION = lltype.Struct('UNION', ('a', lltype.Signed), ('b', lltype.Signed),
                          hints = {'union': True})
    BIG = lltype.GcStruct('BIG', ('u1', UNION), ('u2', UNION))
    def fn():
        x = lltype.malloc(BIG)
        x.u1.a = 3
        x.u2.b = 6
        return x.u1.b * x.u2.a
    check(fn, [], [], Ellipsis)

def test_keep_all_keepalives():
    SIZE = llmemory.sizeof(lltype.Signed)
    PARRAY = lltype.Ptr(lltype.FixedSizeArray(lltype.Signed, 1))
    class A:
        def __init__(self):
            self.addr = llmemory.raw_malloc(SIZE)
        def __del__(self):
            llmemory.raw_free(self.addr)
    class B:
        pass
    def myfunc():
        b = B()
        b.keep = A()
        b.data = llmemory.cast_adr_to_ptr(b.keep.addr, PARRAY)
        b.data[0] = 42
        ptr = b.data
        # normally 'b' could go away as early as here, which would free
        # the memory held by the instance of A in b.keep...
        res = ptr[0]
        # ...so we explicitly keep 'b' alive until here
        objectmodel.keepalive_until_here(b)
        return res
    graph = check(myfunc, [], [], 42,
                  must_be_removed=False)    # 'A' instance left

    # there is a getarrayitem near the end of the graph of myfunc.
    # However, the memory it accesses must still be protected by the
    # following keepalive, even after malloc removal
    entrymap = mkentrymap(graph)
    [link] = entrymap[graph.returnblock]
    assert link.prevblock.operations[-1].opname == 'keepalive'
