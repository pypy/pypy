from rpython.translator.translator import TranslationContext, graphof
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rlib.objectmodel import sandbox_review

from rpython.translator.sandbox.graphchecker import GraphChecker
from rpython.translator.sandbox.graphchecker import make_abort_graph


class TestGraphIsUnsafe(object):

    def graph_is_unsafe(self, fn, signature=[]):
        t = TranslationContext()
        self.t = t
        t.buildannotator().build_types(fn, signature)
        t.buildrtyper().specialize()
        graph = graphof(t, fn)

        checker = GraphChecker(t)
        return checker.graph_is_unsafe(graph)

    def check_safe(self, fn, signature=[]):
        result = self.graph_is_unsafe(fn, signature)
        assert result is None

    def check_unsafe(self, error_substring, fn, signature=[]):
        result = self.graph_is_unsafe(fn, signature)
        assert result is not None
        assert error_substring in result

    def test_simple(self):
        def f():
            pass
        self.check_safe(f)

    def test_unsafe_setfield(self):
        S = lltype.Struct('S', ('x', lltype.Signed))
        s = lltype.malloc(S, flavor='raw', immortal=True)
        def f():
            s.x = 42
        self.check_unsafe("non-GC memory write", f)

    def test_unsafe_operation(self):
        def f():
            llop.debug_forked(lltype.Void)
        self.check_unsafe("unsupported llop", f)

    def test_force_cast(self):
        SRAW = lltype.Struct('SRAW', ('x', lltype.Signed))
        SGC = lltype.GcStruct('SGC', ('x', lltype.Signed))
        def f(x):
            return llop.force_cast(lltype.Signed, x)
        self.check_safe(f, [float])
        self.check_safe(f, [lltype.Ptr(SRAW)])
        self.check_safe(f, [lltype.Ptr(SGC)])
        #
        def g(x):
            return llop.force_cast(lltype.Ptr(SGC), x)
        self.check_unsafe("result is a GC ptr", g, [int])

    def test_direct_call_to_check_caller(self):
        @sandbox_review(check_caller=True)
        def g():
            pass
        def f():
            g()
        self.check_unsafe("direct_call to a graph with check_caller=True", f)

    def test_direct_call_to_reviewed(self):
        @sandbox_review(reviewed=True)
        def g():
            pass
        def f():
            g()
        self.check_safe(f)

    def test_direct_call_to_abort(self):
        @sandbox_review(abort=True)
        def g():
            pass
        def f():
            g()
        self.check_safe(f)

    def test_indirect_call_to_check_caller(self):
        class A:
            def meth(self, i):
                pass
        class B(A):
            def meth(self, i):
                pass
        class C(A):
            @sandbox_review(check_caller=True)
            def meth(self, i):
                pass
        def f(i):
            if i > 5:
                x = B()
            else:
                x = C()
            x.meth(i)
        self.check_unsafe("indirect_call that can go to at least one "
                          "graph with check_caller=True", f, [int])

    def test_direct_call_external(self):
        llfn1 = rffi.llexternal("foobar", [], lltype.Void, sandboxsafe=True,
                                _nowrapper=True)
        self.check_safe(lambda: llfn1())
        #
        llfn2 = rffi.llexternal("foobar", [], lltype.Void, sandboxsafe=False,
                                _nowrapper=True)
        self.check_safe(lambda: llfn2())   # will be turned into an I/O stub
        #
        llfn2b = rffi.llexternal("foobar", [], lltype.Void,
                                 sandboxsafe="check_caller",
                                 _nowrapper=True)
        self.check_unsafe("direct_call to llfunc with "
                          "sandboxsafe='check_caller'", lambda: llfn2b())
        #
        llfn3 = rffi.llexternal("foobar", [], lltype.Void, sandboxsafe=True)
        self.check_safe(lambda: llfn3())
        #
        llfn4 = rffi.llexternal("foobar", [], lltype.Void, sandboxsafe=False)
        self.check_safe(lambda: llfn4())

    def test_make_abort_graph(self):
        def dummy():
            pass
        self.check_safe(dummy)
        graph = graphof(self.t, dummy)
        make_abort_graph(graph)
        assert graph.startblock.operations[0].opname == 'debug_fatalerror'
