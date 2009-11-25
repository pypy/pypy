"""
This is a test that translates a complete JIT to C and runs it.  It is
not testing much, expect that it basically works.  What it *is* testing,
however, is the correct handling of GC, i.e. if objects are freed as
soon as possible (at least in a simple case).
"""
import weakref
import py
from pypy.rlib import rgc
from pypy.rlib.jit import JitDriver
from pypy.jit.backend.llvm.runner import LLVMCPU


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
            r = g(2000)
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
    from pypy.annotation.listdef import s_list_of_strings
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import apply_jit
    from pypy.translator.c import genc
    #
    t = TranslationContext()
    t.config.translation.gc = gc
    t.config.translation.gcconfig.debugprint = True
    for name, value in kwds.items():
        setattr(t.config.translation, name, value)
    t.buildannotator().build_types(f, [s_list_of_strings])
    t.buildrtyper().specialize()
    if kwds['jit']:
        apply_jit(t, CPUClass=LLVMCPU)
    cbuilder = genc.CStandaloneBuilder(t, f, t.config)
    cbuilder.generate_source()
    cbuilder.compile()
    #
    data = cbuilder.cmdexec('')
    return data.splitlines()[-1].strip()


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
