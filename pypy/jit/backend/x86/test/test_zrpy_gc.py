"""
This is a test that translates a complete JIT to C and runs it.  It is
not testing much, expect that it basically works.  What it *is* testing,
however, is the correct handling of GC, i.e. if objects are freed as
soon as possible (at least in a simple case).
"""
import weakref
from pypy.rlib import rgc
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.jit import JitDriver
from pypy.jit.backend.x86.runner import CPU386


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

def f(args):
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


def compile_and_run(gc, **kwds):
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import apply_jit
    from pypy.translator.c import genc
    #
    t = TranslationContext()
    t.config.translation.gc = gc
    t.config.translation.jit = True
    for name, value in kwds.items():
        setattr(t.config.translation, name, value)
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    apply_jit(t, CPUClass=CPU386)
    cbuilder = genc.CStandaloneBuilder(t, f, t.config)
    cbuilder.generate_source()
    cbuilder.compile()
    #
    data = cbuilder.cmdexec('')
    res = int(data.strip())
    if gc == "boehm":
        assert res >= 16
    else:
        assert res == 20


def test_compile_boehm():
    compile_and_run("boehm")

def test_compile_semispace():
    # a moving GC, but with no write barrier
    compile_and_run("semispace", gcrootfinder="asmgcc")
