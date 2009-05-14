"""
This is a test that translates a complete JIT to C and runs it.  It is
not testing much, expect that it basically works.  What it *is* testing,
however, is the correct handling of GC, i.e. if objects are freed as
soon as possible (at least in a simple case).
"""
import weakref, random
import py
from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.jit import JitDriver
from pypy.jit.backend.x86.runner import CPU386
from pypy.jit.backend.x86.gc import GcRefList, GcRootMap_asmgcc
from pypy.jit.backend.x86.regalloc import stack_pos


class X(object):
    next = None

def get_test(main):
    main._dont_inline_ = True

    def g(n):
        x = X()
        x.foo = 2
        main(n, x)
        x.foo = 5
        return weakref.ref(x)
    g._dont_inline_ = True

    def entrypoint(args):
        r_list = []
        for i in range(20):
            r = g(1000)
            r_list.append(r)
            rgc.collect()
        rgc.collect(); rgc.collect()
        freed = 0
        for r in r_list:
            if r() is None:
                freed += 1
        print freed
        return 0

    return entrypoint


def compile_and_run(f, gc, **kwds):
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import apply_jit
    from pypy.translator.c import genc
    #
    t = TranslationContext()
    t.config.translation.gc = gc
    for name, value in kwds.items():
        setattr(t.config.translation, name, value)
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    if kwds['jit']:
        apply_jit(t, CPUClass=CPU386)
    cbuilder = genc.CStandaloneBuilder(t, f, t.config)
    cbuilder.generate_source()
    cbuilder.compile()
    #
    data = cbuilder.cmdexec('')
    return data.strip()


def test_compile_boehm():
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            y = X()
            y.foo = x.foo
            n -= y.foo
    res = compile_and_run(get_test(main), "boehm", jit=True)
    assert int(res) >= 16

def test_GcRefList():
    S = lltype.GcStruct('S')
    order = range(20000) * 4
    random.shuffle(order)
    def fn(args):
        allocs = [lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))
                  for i in range(20000)]
        allocs = [allocs[i] for i in order]
        #
        gcrefs = GcRefList()
        addrs = [gcrefs.get_address_of_gcref(ptr) for ptr in allocs]
        for i in range(len(allocs)):
            assert addrs[i].address[0] == llmemory.cast_ptr_to_adr(allocs[i])
        return 0
    compile_and_run(fn, "hybrid", gcrootfinder="asmgcc", jit=False)

def test_compile_hybrid_1():
    # a moving GC.  Supports malloc_varsize_nonmovable.  Simple test, works
    # without write_barriers and root stack enumeration.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            y = X()
            y.foo = x.foo
            n -= y.foo
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_GcRootMap_asmgcc():
    gcrootmap = GcRootMap_asmgcc()
    shape = gcrootmap._get_callshape([stack_pos(1), stack_pos(55)])
    assert shape == [6, 1, 5, 9, 2, 0, 4|3, 220|3]
    #
    shapeaddr = gcrootmap.encode_callshape([stack_pos(1), stack_pos(55)])
    PCALLSHAPE = lltype.Ptr(GcRootMap_asmgcc.CALLSHAPE_ARRAY)
    p = llmemory.cast_adr_to_ptr(shapeaddr, PCALLSHAPE)
    for i, expected in enumerate([131, 62, 14, 0, 4, 18, 10, 2, 12]):
        assert p[i] == expected
    #
    retaddr = rffi.cast(llmemory.Address, 1234567890)
    gcrootmap.put(retaddr, shapeaddr)
    assert gcrootmap._gcmap[0] == retaddr
    assert gcrootmap._gcmap[1] == shapeaddr
    assert gcrootmap.gcmapstart().address[0] == retaddr
    #
    # the same as before, but enough times to trigger a few resizes
    expected_shapeaddr = {}
    for i in range(1, 600):
        shapeaddr = gcrootmap.encode_callshape([stack_pos(i)])
        expected_shapeaddr[i] = shapeaddr
        retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        gcrootmap.put(retaddr, shapeaddr)
    for i in range(1, 600):
        expected_retaddr = rffi.cast(llmemory.Address, 123456789 + i)
        assert gcrootmap._gcmap[i*2+0] == expected_retaddr
        assert gcrootmap._gcmap[i*2+1] == expected_shapeaddr[i]

def test_compile_hybrid_2():
    # More complex test, requires root stack enumeration but
    # not write_barriers.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            prev = x
            for j in range(101):    # main() runs 20'000 times, thus allocates
                y = X()             # a total of 2'020'000 objects
                y.foo = prev.foo
                prev = y
            n -= prev.foo
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20

def test_compile_hybrid_3():
    py.test.skip("in-progress")
    # Third version of the test.  Really requires write_barriers.
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            x.next = None
            for j in range(101):    # main() runs 20'000 times, thus allocates
                y = X()             # a total of 2'020'000 objects
                y.foo = j+1
                y.next = x.next
                x.next = y
            total = 0
            y = x
            for j in range(101):
                y = y.next
                total += y.foo
            assert not y.next
            assert total == 101*102/2
            n -= x.foo
    x_test = X()
    x_test.foo = 5
    main(6, x_test)     # check that it does not raise AssertionError
    res = compile_and_run(get_test(main), "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20
