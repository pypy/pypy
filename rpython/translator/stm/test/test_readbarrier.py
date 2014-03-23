from rpython.rlib.objectmodel import stm_ignored
from rpython.translator.stm.test.transform_support import BaseTestTransform
from rpython.rtyper.lltypesystem import lltype


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
