import py
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.rthread import ThreadLocalReference
from rpython.rlib.jit import dont_look_inside


class ThreadLocalTest(object):

    def test_threadlocalref_get(self):
        class Foo:
            pass
        t = ThreadLocalReference(Foo)
        x = Foo()

        @dont_look_inside
        def setup():
            t.set(x)

        def f():
            setup()
            if t.get() is x:
                return 42
            return -666

        res = self.interp_operations(f, [])
        assert res == 42


class TestLLtype(ThreadLocalTest, LLJitMixin):
    pass
