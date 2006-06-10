from pypy.rpython.lltypesystem.lltype import *
from pypy.translator.c.test import test_typed


class TestLowLevelType(test_typed.CompilationTestCase):

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
            a7.item6 = -2
            a3[0].v = -3
            a3[2].v = -4
            a42[0][0] = -5
            a42[5][6] = -6
            assert a7[0] == -1
            assert a7[6] == -2
            assert a3[0].v == -3
            assert a3.item2.v == -4
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

    def test_call_with_fixedsizearray(self):
        A = FixedSizeArray(Struct('s1', ('x', Signed)), 5)
        S = GcStruct('s', ('a', Ptr(A)))
        a = malloc(A, immortal=True)
        a[1].x = 123
        def g(x):
            return x[1].x
        def llf():
            s = malloc(S)
            s.a = a
            return g(s.a)
        fn = self.getcompiled(llf)
        res = fn()
        assert res == 123

    def test_more_prebuilt_arrays(self):
        A = FixedSizeArray(Struct('s1', ('x', Signed)), 5)
        S = GcStruct('s', ('a1', Ptr(A)), ('a2', A))
        s = malloc(S)
        s.a1 = malloc(A, immortal=True)
        s.a1[2].x = 50
        s.a2[2].x = 60
        def llf(n=int):
            if n == 1:
                a = s.a1
            else:
                a = s.a2
            return a[2].x
        fn = self.getcompiled(llf)
        res = fn(1)
        assert res == 50
        res = fn(2)
        assert res == 60

    def test_fnptr_with_fixedsizearray(self):
        A = ForwardReference()
        F = FuncType([Ptr(A)], Signed)
        A.become(FixedSizeArray(Struct('s1', ('f', Ptr(F)), ('n', Signed)), 5))
        a = malloc(A, immortal=True)
        a[3].n = 42
        def llf(n=int):
            if a[n].f:
                return a[n].f(a)
            else:
                return -1
        fn = self.getcompiled(llf)
        res = fn(4)
        assert res == -1

    def test_direct_arrayitems(self):
        for a in [malloc(GcArray(Signed), 5),
                  malloc(FixedSizeArray(Signed, 5), immortal=True)]:
            a[0] = 0
            a[1] = 10
            a[2] = 20
            a[3] = 30
            a[4] = 40
            b0 = direct_arrayitems(a)
            b1 = direct_ptradd(b0, 1)
            b2 = direct_ptradd(b1, 1)
            def llf(n=int):
                b0 = direct_arrayitems(a)
                b3 = direct_ptradd(direct_ptradd(b0, 5), -2)
                saved = a[n]
                a[n] = 1000
                try:
                    return b0[0] + b3[-2] + b2[1] + b1[3]
                finally:
                    a[n] = saved
            fn = self.getcompiled(llf)
            res = fn(0)
            assert res == 1000 + 10 + 30 + 40
            res = fn(1)
            assert res == 0 + 1000 + 30 + 40
            res = fn(2)
            assert res == 0 + 10 + 30 + 40
            res = fn(3)
            assert res == 0 + 10 + 1000 + 40
            res = fn(4)
            assert res == 0 + 10 + 30 + 1000

    def test_direct_fieldptr(self):
        S = GcStruct('S', ('x', Signed), ('y', Signed))
        def llf(n=int):
            s = malloc(S)
            a = direct_fieldptr(s, 'y')
            a[0] = n
            return s.y

        fn = self.getcompiled(llf)
        res = fn(34)
        assert res == 34

    def test_prebuilt_subarrays(self):
        a1 = malloc(GcArray(Signed), 5)
        a2 = malloc(FixedSizeArray(Signed, 5), immortal=True)
        s  = malloc(GcStruct('S', ('x', Signed), ('y', Signed)))
        a1[3] = 7000
        a2[1] =  600
        s.x   =   50
        s.y   =    4
        p1 = direct_ptradd(direct_arrayitems(a1), 3)
        p2 = direct_ptradd(direct_arrayitems(a2), 1)
        p3 = direct_fieldptr(s, 'x')
        p4 = direct_fieldptr(s, 'y')
        def llf():
            a1[3] += 1000
            a2[1] +=  100
            s.x   +=   10
            s.y   +=    1
            return p1[0] + p2[0] + p3[0] + p4[0]

        fn = self.getcompiled(llf)
        res = fn()
        assert res == 8765

    def test_pystruct(self):
        PS1 = PyStruct('PS1', ('head', PyObject), ('x', Signed),
                       hints = {'inline_head': True})
        class mytype(object):
            pass
        mytype_ptr = pyobjectptr(mytype)
        def llf():
            p = malloc(PS1, flavor='cpy', extra_args=(mytype_ptr,))
            return cast_pointer(Ptr(PyObject), p)

        fn = self.getcompiled(llf)
        res = fn()
        assert type(res).__name__.endswith('mytype')

    def test_pystruct_prebuilt(self):
        PS1 = PyStruct('PS1', ('head', PyObject), ('x', Signed),
                       hints = {'inline_head': True})
        class mytype(object):
            pass

        def llsetup(phead):
            "Called when the CPython ext module is imported."
            p = cast_pointer(Ptr(PS1), phead)
            p.x = 27

        mytype_ptr = pyobjectptr(mytype)
        p = malloc(PS1, flavor='cpy', extra_args=(mytype_ptr,))
        p.x = -5   # overridden by llsetup()

        def llf():
            return p.x

        def process(t):
            rtyper = t.buildrtyper()
            rtyper.specialize()
            llsetup_ptr = rtyper.annotate_helper_fn(llsetup, [Ptr(PyObject)])
            phead = cast_pointer(Ptr(PyObject), p)
            phead._obj.setup_fnptr = llsetup_ptr

        self.process = process
        fn = self.getcompiled(llf)
        res = fn()
        assert res == 27
