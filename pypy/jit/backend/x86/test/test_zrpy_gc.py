"""
This is a test that translates a complete JIT to C and runs it.  It is
not testing much, expect that it basically works.  What it *is* testing,
however, is the correct handling of GC, i.e. if objects are freed as
soon as possible (at least in a simple case).
"""
import weakref, random
import py
from pypy.rlib import rgc
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.jit import JitDriver
from pypy.jit.backend.x86.runner import CPU386
from pypy.jit.backend.x86.gc import GcRefList


myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])


class X(object):
    pass

def main(n, x):
    while n > 0:
        myjitdriver.can_enter_jit(n=n, x=x)
        myjitdriver.jit_merge_point(n=n, x=x)
        y = X()
        y.foo = x.foo
        n -= y.foo
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
    res = compile_and_run(entrypoint, "boehm", jit=True)
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

def test_compile_hybrid():
    # a moving GC, with a write barrier.  Supports malloc_varsize_nonmovable.
    res = compile_and_run(entrypoint, "hybrid", gcrootfinder="asmgcc",
                          jit=True)
    assert int(res) == 20
