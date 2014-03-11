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
