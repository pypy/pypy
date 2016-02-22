from rpython.rlib.objectmodel import stm_ignored
from rpython.translator.stm.test.transform_support import BaseTestTransform
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop


class TestReadBarrier(BaseTestTransform):
    do_read_barrier = True

    def test_simple_read(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42
        x2 = lltype.malloc(X, immortal=True)
        x2.foo = 81

        def f1(n):
            if n > 1:
                return x2.foo
            else:
                return x1.foo

        res = self.interpret(f1, [4])
        assert res == 81
        assert self.read_barriers == [x2]
        res = self.interpret(f1, [-5])
        assert res == 42
        assert self.read_barriers == [x1]

    def test_simple_read_after_write(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(n):
            x1.foo = 7 # write barrier will be done
            return x1.foo

        res = self.interpret(f1, [4])
        assert res == 7
        assert self.read_barriers == [] # implicitly by the write-barrier

    def test_stm_ignored_read(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42
        def f1():
            with stm_ignored:
                return x1.foo
        res = self.interpret(f1, [])
        assert res == 42
        assert self.read_barriers == []

    def test_getarrayitem(self):
        X = lltype.GcArray(lltype.Signed)
        x1 = lltype.malloc(X, 5, immortal=True, zero=True)
        x1[2] = 42

        def f1(n):
            return x1[n]

        res = self.interpret(f1, [2])
        assert res == 42
        assert self.read_barriers == [x1]

    def test_array_size(self):
        array_gc = lltype.GcArray(('z', lltype.Signed))
        array_nongc = lltype.Array(('z', lltype.Signed))
        Q = lltype.GcStruct('Q',
                            ('gc', lltype.Ptr(array_gc)),
                            ('raw', lltype.Ptr(array_nongc)))
        q = lltype.malloc(Q, immortal=True)
        q.gc = lltype.malloc(array_gc, n=3, flavor='gc', immortal=True)
        q.raw = lltype.malloc(array_nongc, n=5, flavor='raw', immortal=True)
        def f1(n):
            if n == 1:
                return len(q.gc)
            else:
                return len(q.raw)
        res = self.interpret(f1, [1])
        assert self.read_barriers == [q]
        res = self.interpret(f1, [0])
        assert self.read_barriers == [q]


    def test_multiple_reads(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed),
                                 ('bar', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 6
        x1.bar = 7
        x2 = lltype.malloc(X, immortal=True)
        x2.foo = 81
        x2.bar = -1

        def f1(n):
            if n > 1:
                return x2.foo * x2.bar
            else:
                return x1.foo * x1.bar

        res = self.interpret(f1, [4])
        assert res == -81
        assert self.read_barriers == [x2]


    def test_dont_repeat_read_barrier_after_malloc(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True, zero=True)
        def f1(n):
            t1 = x1.foo
            lltype.malloc(X)
            t1 += x1.foo
            return t1

        self.interpret(f1, [4])
        assert self.read_barriers == [x1]

    def test_call_external_release_gil(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(p):
            x1 = p.foo
            external_release_gil()
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        res = self.interpret(f1, [x])
        assert res == 36
        assert self.read_barriers == [x, x]

    def test_call_external_any_gcobj(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(p):
            x1 = p.foo
            external_any_gcobj()
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        res = self.interpret(f1, [x])
        assert res == 36
        assert self.read_barriers == [x]

    def test_call_external_safest(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(p):
            x1 = p.foo
            external_safest()
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        res = self.interpret(f1, [x])
        assert res == 36
        assert self.read_barriers == [x]

    def test_simple_loop(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, i):
            while i > 0:
                i -= x.foo
            return i
        x = lltype.malloc(X, immortal=True); x.foo = 1
        res = self.interpret(f1, [x, 5])
        assert res == 0
        # for now we get this.  Later, we could probably optimize it
        assert self.read_barriers == [x] * 5


    def test_read_immutable(self):
        class Foo:
            _immutable_ = True

        def f1(n):
            x = Foo()
            x.foo = 4
            llop.debug_stm_flush_barrier(lltype.Void)
            if n > 1:
                n = x.foo
            llop.debug_stm_flush_barrier(lltype.Void)
            return x.foo + n

        res = self.interpret(f1, [4])
        assert res == 8
        assert len(self.read_barriers) == 0

    def test_read_immutable_prebuilt(self):
        class Foo:
            _immutable_ = True
        x1 = Foo()
        x1.foo = 42
        x2 = Foo()
        x2.foo = 81

        def f1(n):
            if n > 1:
                return x2.foo
            else:
                return x1.foo

        res = self.interpret(f1, [4])
        assert res == 81
        assert self.read_barriers == []

    def test_immut_barrier_before_weakref_deref(self):
        import weakref
        class Foo:
            pass

        def f1():
            x = Foo()
            w = weakref.ref(x)
            llop.debug_stm_flush_barrier(lltype.Void)
            return w()

        self.interpret(f1, [])
        assert len(self.read_barriers) == 1


    def test_transaction_breaking_ops(self):
        class X:
            a = 1
        x = X()

        def f1(f):
            x.a = f
            t = x.a # no read barrier
            llop.stm_leave_transactional_zone(lltype.Void)
            t += x.a
            llop.stm_enter_transactional_zone(lltype.Void)
            t += x.a
            llop.stm_transaction_break(lltype.Void)
            t += x.a
            llop.stm_enter_callback_call(lltype.Void)
            t += x.a
            llop.stm_leave_callback_call(lltype.Void)
            t += x.a
            return t

        self.interpret(f1, [1])
        assert len(self.read_barriers) == 5




# class TestAfterGCTransform(BaseTestTransform):
#     do_read_barrier = True
#     do_gc_transform = True

#     def test_malloc_result_readable(self):
#         from rpython.flowspace.model import summary
#         X = lltype.GcStruct('X', ('foo', lltype.Signed))
#         #
#         def nobreak_escape(x):
#             x.foo = 7
#             return x
#         nobreak_escape._dont_inline_ = True
#         #
#         def f1(n):
#             x = lltype.malloc(X)
#             t = x.foo
#             nobreak_escape(x)
#             return t

#         self.interpret(f1, [4], run=False)
#         g = self.graph
#         from rpython.translator.translator import graphof
#         #ff = graphof(g, f1)
#         #ff.show()
#         assert summary(g)['stm_read'] == 0

#         assert self.read_barriers == [x1]


external_release_gil = rffi.llexternal('external_release_gil', [], lltype.Void,
                                       _callable=lambda: None,
                                       random_effects_on_gcobjs=True,
                                       releasegil=True)   # GIL is released
external_any_gcobj = rffi.llexternal('external_any_gcobj', [], lltype.Void,
                                     _callable=lambda: None,
                                     random_effects_on_gcobjs=True,
                                     releasegil=False)   # GIL is not released
external_safest = rffi.llexternal('external_safest', [], lltype.Void,
                                  _callable=lambda: None,
                                  random_effects_on_gcobjs=False,
                                  releasegil=False)   # GIL is not released
