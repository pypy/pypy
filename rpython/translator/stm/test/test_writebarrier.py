from rpython.rlib.rstm import register_invoke_around_extcall
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.stm.test.transform_support import BaseTestTransform


class TestTransform(BaseTestTransform):
    do_write_barrier = True

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
        assert len(self.writemode) == 0
        res = self.interpret(f1, [-5])
        assert res == 42
        assert len(self.writemode) == 0
        assert self.barriers == ['I2R']

    def test_simple_write(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 42

        def f1(n):
            x1.foo = n

        self.interpret(f1, [4])
        assert x1.foo == 4
        assert len(self.writemode) == 1
        assert self.barriers == ['I2W']

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
        assert len(self.writemode) == 0
        assert self.barriers == ['I2R']

    def test_malloc(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(n):
            p = lltype.malloc(X)
            p.foo = n

        self.interpret(f1, [4])
        assert len(self.writemode) == 1
        assert self.barriers == []

    def test_repeat_write_barrier_after_malloc(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        x1 = lltype.malloc(X, immortal=True)
        x1.foo = 6
        def f1(n):
            x1.foo = n
            lltype.malloc(X)
            x1.foo = x1.foo + n

        self.interpret(f1, [4])
        assert len(self.writemode) == 2
        assert self.barriers == ['I2W', 'V2W']

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
        assert len(self.writemode) == 1
        assert self.barriers == ['I2R']

    def test_write_may_alias(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(p, q):
            x1 = p.foo
            q.foo = 7
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 36
        assert self.barriers == ['A2R', 'A2W', 'q2r']
        res = self.interpret(f1, [x, x])
        assert res == 42
        assert self.barriers == ['A2R', 'A2W', 'Q2R']

    def test_write_cannot_alias(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        Y = lltype.GcStruct('Y', ('foo', lltype.Signed))
        def f1(p, q):
            x1 = p.foo
            q.foo = 7
            x2 = p.foo
            return x1 * x2

        x = lltype.malloc(X, immortal=True); x.foo = 6
        y = lltype.malloc(Y, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 36
        assert self.barriers == ['A2R', 'A2W']

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
        assert self.barriers == ['A2R', 'I2R']

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
        assert self.barriers == ['A2R', 'q2r']

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
        assert self.barriers == ['A2R']

    def test_pointer_compare_0(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x):
            return x != lltype.nullptr(X)
        x = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x])
        assert res == 1
        assert self.barriers == []

    def test_pointer_compare_1(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            return x != y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 1
        assert self.barriers == ['=']
        res = self.interpret(f1, [x, x])
        assert res == 0
        assert self.barriers == ['=']

    def test_pointer_compare_2(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            x.foo = 41
            return x == y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 0
        assert self.barriers == ['A2W', '=']
        res = self.interpret(f1, [x, x])
        assert res == 1
        assert self.barriers == ['A2W', '=']

    def test_pointer_compare_3(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            y.foo = 41
            return x != y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 1
        assert self.barriers == ['A2W', '=']
        res = self.interpret(f1, [x, x])
        assert res == 0
        assert self.barriers == ['A2W', '=']

    def test_pointer_compare_4(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, y):
            x.foo = 40
            y.foo = 41
            return x != y
        x = lltype.malloc(X, immortal=True)
        y = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, y])
        assert res == 1
        assert self.barriers == ['A2W', 'A2W']
        res = self.interpret(f1, [x, x])
        assert res == 0
        assert self.barriers == ['A2W', 'A2W']

    def test_simple_loop(self):
        X = lltype.GcStruct('X', ('foo', lltype.Signed))
        def f1(x, i):
            while i > 0:
                x.foo = i
                i -= 1
            return i
        x = lltype.malloc(X, immortal=True)
        res = self.interpret(f1, [x, 5])
        assert res == 0
        # for now we get this.  Later, we could probably optimize it
        assert self.barriers == ['A2W', 'a2w', 'a2w', 'a2w', 'a2w']

    def test_subclassing(self):
        class X:
            __slots__ = ['foo']
        class Y(X):
            pass
        class Z(X):
            pass
        def f1(i):
            if i > 5:
                x = Y()
                x.foo = 42
                x.ybar = i
            else:
                x = Z()
                x.foo = 815
                x.zbar = 'A'
            external_any_gcobj()
            result = x.foo          # 1
            if isinstance(x, Y):    # 2
                result += x.ybar    # 3
            return result

        res = self.interpret(f1, [10])
        assert res == 42 + 10
        assert self.barriers == ['a2r', 'a2i', 'a2r'] # from 3 blocks (could be
                                                      # optimized later)
        res = self.interpret(f1, [-10])
        assert res == 815
        assert self.barriers == ['a2r', 'a2i']

    def test_write_barrier_repeated(self):
        class X:
            pass
        x = X()
        def f1(i):
            x.a = i   # write barrier
            y = X()   # malloc
            x.a += 1  # write barrier again
            return y

        res = self.interpret(f1, [10])
        assert self.barriers == ['I2W', 'V2W']

    def test_read_immutable(self):
        class Foo:
            _immutable_ = True

        def f1(n):
            x = Foo()
            if n > 1:
                x.foo = n
            return x.foo

        res = self.interpret(f1, [4])
        assert res == 4
        assert self.barriers == ['a2w', 'a2i']

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
        assert self.barriers == []


external_release_gil = rffi.llexternal('external_release_gil', [], lltype.Void,
                                       _callable=lambda: None,
                                       random_effects_on_gcobjs=True,
                                       threadsafe=True)   # GIL is released
external_any_gcobj = rffi.llexternal('external_any_gcobj', [], lltype.Void,
                                     _callable=lambda: None,
                                     random_effects_on_gcobjs=True,
                                     threadsafe=False)   # GIL is not released
external_safest = rffi.llexternal('external_safest', [], lltype.Void,
                                  _callable=lambda: None,
                                  random_effects_on_gcobjs=False,
                                  threadsafe=False)   # GIL is not released
