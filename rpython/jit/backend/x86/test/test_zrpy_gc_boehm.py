
import weakref
from rpython.rlib.jit import JitDriver, dont_look_inside
from rpython.jit.backend.x86.test.test_zrpy_gc import run, get_entry, compile
from rpython.jit.backend.x86.test.test_ztranslation import fix_annotator_for_vrawbuffer

class X(object):
    def __init__(self, x=0):
        self.x = x

    next = None

class CheckError(Exception):
    pass

def check(flag):
    if not flag:
        raise CheckError

def compile_and_run(f, gc, **kwds):
    cbuilder = compile(f, gc, **kwds)
    return run(cbuilder)

def get_g(main):
    main._dont_inline_ = True
    def g(name, n):
        x = X()
        x.foo = 2
        main(n, x)
        x.foo = 5
        return weakref.ref(x)
    g._dont_inline_ = True
    return g

def test_compile_boehm(monkeypatch):
    fix_annotator_for_vrawbuffer(monkeypatch)
    myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
    @dont_look_inside
    def see(lst, n):
        assert len(lst) == 3
        assert lst[0] == n+10
        assert lst[1] == n+20
        assert lst[2] == n+30
    def main(n, x):
        while n > 0:
            myjitdriver.can_enter_jit(n=n, x=x)
            myjitdriver.jit_merge_point(n=n, x=x)
            y = X()
            y.foo = x.foo
            n -= y.foo
            see([n+10, n+20, n+30], n)
    res = compile_and_run(get_entry(get_g(main)), "boehm", jit=True)
    assert int(res) >= 16
