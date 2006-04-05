from pypy.rpython.lltypesystem.lltype import *
from pypy.translator.c.test import test_typed


class TestLowLevelType:
    getcompiled = test_typed.TestTypedTestCase().getcompiled

    def test_simple(self):
        S = GcStruct("s", ('v', Signed))
        def llf():
            s = malloc(S)
            return s.v
        fn = self.getcompiled(llf)
        assert fn() == 0

    def test_simple2(self):
        S = Struct("s", ('v', Signed))
        S2 = GcStruct("s2", ('a',S), ('b',S))
        def llf():
            s = malloc(S2)
            s.a.v = 6
            s.b.v = 12
            return s.a.v + s.b.v
        fn = self.getcompiled(llf)
        assert fn() == 18

    def test_fixedsizearray(self):
        S = Struct("s", ('v', Signed))
        A7 = FixedSizeArray(Signed, 7)
        A3 = FixedSizeArray(S, 3)
        A42 = FixedSizeArray(A7, 6)
        BIG = GcStruct("big", ("a7", A7), ("a3", A3), ("a42", A42))
        def llf():
            big = malloc(BIG)
            a7 = big.a7
            a3 = big.a3
            a42 = big.a42
            a7[0] = -1
            a7[6] = -2
            a3[0].v = -3
            a3[2].v = -4
            a42[0][0] = -5
            a42[5][6] = -6
            assert a7[0] == -1
            assert a7[6] == -2
            assert a3[0].v == -3
            assert a3[2].v == -4
            assert a42[0][0] == -5
            assert a42[5][6] == -6
            return len(a42)*100 + len(a42[4])
        fn = self.getcompiled(llf)
        res = fn()
        assert fn() == 607

    def test_recursivearray(self):
        A = ForwardReference()
        A.become(FixedSizeArray(Struct("S", ('a', Ptr(A))), 5))
        TREE = GcStruct("TREE", ("root", A), ("other", A))
        def llf():
            tree = malloc(TREE)
            tree.root[0].a = tree.root
            tree.root[1].a = tree.other
            assert tree.root[0].a[0].a[0].a[0].a[0].a[1].a == tree.other
        fn = self.getcompiled(llf)
        fn()

    def test_prebuilt_array(self):
        A = FixedSizeArray(Signed, 5)
        a = malloc(A, immortal=True)
        a[0] = 8
        a[1] = 5
        a[2] = 12
        a[3] = 12
        a[4] = 15
        def llf():
            s = ''
            for i in range(5):
                s += chr(64+a[i])
            assert s == "HELLO"
        fn = self.getcompiled(llf)
        fn()
