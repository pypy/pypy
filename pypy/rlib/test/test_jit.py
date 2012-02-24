import py
from pypy.conftest import option
from pypy.rlib.jit import hint, we_are_jitted, JitDriver, elidable_promote
from pypy.rlib.jit import JitHintError, oopspec, isconstant
from pypy.rlib.rarithmetic import r_uint
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.lltypesystem import lltype

def test_oopspec():
    @oopspec('foobar')
    def fn():
        pass
    assert fn.oopspec == 'foobar'
    
class BaseTestJIT(BaseRtypingTest):
    def test_hint(self):
        def f():
            x = hint(5, hello="world")
            return x
        res = self.interpret(f, [])
        assert res == 5

    def test_we_are_jitted(self):
        def f(x):
            try:
                if we_are_jitted():
                    return x
                return x + 1
            except Exception:
                return 5
        res = self.interpret(f, [4])
        assert res == 5

    def test_elidable_promote(self):
        @elidable_promote()
        def g(func):
            return func + 1
        def f(x):
            return g(x * 2)
        res = self.interpret(f, [2])
        assert res == 5

    def test_elidable_promote_args(self):
        @elidable_promote(promote_args='0')
        def g(func, x):
            return func + 1
        def f(x):
            return g(x * 2, x)
        
        import dis
        from StringIO import StringIO
        import sys
        
        s = StringIO()
        prev = sys.stdout
        sys.stdout = s
        try:
            dis.dis(g)
        finally:
            sys.stdout = prev
        x = s.getvalue().find('CALL_FUNCTION')
        assert x != -1
        x = s.getvalue().find('CALL_FUNCTION', x)
        assert x != -1
        x = s.getvalue().find('CALL_FUNCTION', x)
        assert x != -1
        res = self.interpret(f, [2])
        assert res == 5

    def test_annotate_hooks(self):
        
        def get_printable_location(m): pass
        
        myjitdriver = JitDriver(greens=['m'], reds=['n'],
                                get_printable_location=get_printable_location)
        def fn(n):
            m = 42.5
            while n > 0:
                myjitdriver.can_enter_jit(m=m, n=n)
                myjitdriver.jit_merge_point(m=m, n=n)
                n -= 1
            return n

        t, rtyper, fngraph = self.gengraph(fn, [int])

        # added by compute_result_annotation()
        assert fn._dont_reach_me_in_del_ == True

        def getargs(func):
            for graph in t.graphs:
                if getattr(graph, 'func', None) is func:
                    return [v.concretetype for v in graph.getargs()]
            raise Exception, 'function %r has not been annotated' % func

        get_printable_location_args = getargs(get_printable_location)
        assert get_printable_location_args == [lltype.Float]

    def test_annotate_argumenterror(self):
        myjitdriver = JitDriver(greens=['m'], reds=['n'])
        def fn(n):
            while n > 0:
                myjitdriver.can_enter_jit(m=42.5, n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            return n
        py.test.raises(JitHintError, self.gengraph, fn, [int])

    def test_annotate_typeerror(self):
        myjitdriver = JitDriver(greens=['m'], reds=['n'])
        class A(object): pass
        class B(object): pass
        def fn(n):
            while n > 0:
                myjitdriver.can_enter_jit(m=A(), n=n)
                myjitdriver.jit_merge_point(m=B(), n=n)
                n -= 1
            return n
        py.test.raises(JitHintError, self.gengraph, fn, [int])

    def test_green_field(self):
        def get_printable_location(xfoo):
            return str(ord(xfoo))   # xfoo must be annotated as a character
        myjitdriver = JitDriver(greens=['x.foo'], reds=['n', 'x'],
                                get_printable_location=get_printable_location)
        class A(object):
            _immutable_fields_ = ['foo']
        def fn(n):
            x = A()
            x.foo = chr(n)
            while n > 0:
                myjitdriver.can_enter_jit(x=x, n=n)
                myjitdriver.jit_merge_point(x=x, n=n)
                n -= 1
            return n
        t = self.gengraph(fn, [int])[0]
        if option.view:
            t.view()
        # assert did not raise

    def test_isconstant(self):
        def f(n):
            assert isconstant(n) is False
            l = []
            l.append(n)
            return len(l)
        res = self.interpret(f, [-234])
        assert res == 1

    def test_argument_order_ok(self):
        myjitdriver = JitDriver(greens=['i1', 'r1', 'f1'], reds=[])
        class A(object):
            pass
        myjitdriver.jit_merge_point(i1=42, r1=A(), f1=3.5)
        # assert did not raise

    def test_argument_order_wrong(self):
        myjitdriver = JitDriver(greens=['r1', 'i1', 'f1'], reds=[])
        class A(object):
            pass
        e = raises(AssertionError,
                   myjitdriver.jit_merge_point, i1=42, r1=A(), f1=3.5)

    def test_argument_order_more_precision_later(self):
        myjitdriver = JitDriver(greens=['r1', 'i1', 'r2', 'f1'], reds=[])
        class A(object):
            pass
        myjitdriver.jit_merge_point(i1=42, r1=None, r2=None, f1=3.5)
        e = raises(AssertionError,
                   myjitdriver.jit_merge_point, i1=42, r1=A(), r2=None, f1=3.5)
        assert "got ['2:REF', '1:INT', '?', '3:FLOAT']" in repr(e.value)

    def test_argument_order_more_precision_later_2(self):
        myjitdriver = JitDriver(greens=['r1', 'i1', 'r2', 'f1'], reds=[])
        class A(object):
            pass
        myjitdriver.jit_merge_point(i1=42, r1=None, r2=A(), f1=3.5)
        e = raises(AssertionError,
                   myjitdriver.jit_merge_point, i1=42, r1=A(), r2=None, f1=3.5)
        assert "got ['2:REF', '1:INT', '2:REF', '3:FLOAT']" in repr(e.value)

    def test_argument_order_accept_r_uint(self):
        # this used to fail on 64-bit, because r_uint == r_ulonglong
        myjitdriver = JitDriver(greens=['i1'], reds=[])
        myjitdriver.jit_merge_point(i1=r_uint(42))


class TestJITLLtype(BaseTestJIT, LLRtypeMixin):
    pass

class TestJITOOtype(BaseTestJIT, OORtypeMixin):
    pass
