from rpython.rlib.objectmodel import stm_ignored
from rpython.translator.stm.test.transform_support import BaseTestTransform
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rstm import register_invoke_around_extcall
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
        self.interpret(f1, [1])
        assert self.read_barriers == [q]
        self.interpret(f1, [0])
        assert self.read_barriers == [q]

    def test_simple_read_2(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x2 = lltype.malloc(X, immortal=True)
        x2.foo = 81
        null = lltype.nullptr(X)

        def f1(n):
            if n < 1:
                p = null
            else:
                p = x2
            return p.foo

        res = self.interpret(f1, [4])
        assert res == 81
        assert self.read_barriers == [x2]


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

    def test_malloc(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(n):
            p = lltype.malloc(X)
            p.foo = n

        self.interpret(f1, [4])
        assert self.read_barriers == []

    def test_repeat_read_barrier_after_malloc(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 6
        def f1(n):
            i = x1.foo
            lltype.malloc(X)
            i = x1.foo + i
            return i

        self.interpret(f1, [4])
        assert self.read_barriers == [x1]

    def test_call_external_release_gil(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(p):
            register_invoke_around_extcall()
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
            register_invoke_around_extcall()
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
            register_invoke_around_extcall()
            x1 = p.foo
            external_safest()
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        res = self.interpret(f1, [x])
        assert res == 36
        assert self.read_barriers == [x]

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
