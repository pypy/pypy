import gc
from rpython.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong
from rpython.translator.c.test.test_typed import TestTypedTestCase as _TestTypedTestCase
from rpython.translator.c.test.test_genc import compile


class TestTypedOptimizedTestCase(_TestTypedTestCase):
    getcompiled = staticmethod(compile)

    def test_remove_same_as(self):
        def f(n):
            if bool(bool(bool(n))):
                return 123
            else:
                return 456
        fn = self.getcompiled(f, [bool])
        assert fn(True) == 123
        assert fn(False) == 456


class TestTypedOptimizedSwitchTestCase:
    def getcompiled(self, func, argtypes):
        return compile(func, argtypes, merge_if_blocks=True)

    def test_int_switch(self):
        def f(x):
            if x == 3:
                return 9
            elif x == 9:
                return 27
            elif x == 27:
                return 3
            return 0
        fn = self.getcompiled(f, [int])
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)

    def test_int_switch_nonsparse(self):
        def f(x):
            if x == 1:
                return 9
            elif x == 2:
                return 27
            elif x == 3:
                return 3
            return 0
        fn = self.getcompiled(f, [int])
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)

    def test_int_switch_nonsparse_neg(self):
        def f(x):
            if x == -1:
                return 9
            elif x == 2:
                return 27
            elif x == 3:
                return 3
            return 0
        fn = self.getcompiled(f, [int])
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)

    def test_uint_switch(self):
        def f(x):
            if x == r_uint(3):
                return 9
            elif x == r_uint(9):
                return 27
            elif x == r_uint(27):
                return 3
            return 0
        fn = self.getcompiled(f, [r_uint])
        for x in (0,1,2,3,9,27,48):
            assert fn(r_uint(x)) == f(r_uint(x))

    def test_longlong_switch(self):
        def f(x):
            if x == r_longlong(3):
                return 9
            elif x == r_longlong(9):
                return 27
            elif x == r_longlong(27):
                return 3
            return 0
        fn = self.getcompiled(f, [r_longlong])
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(r_longlong(x)) == f(r_longlong(x))

    def test_ulonglong_switch(self):
        def f(x):
            if x == r_ulonglong(3):
                return 9
            elif x == r_ulonglong(9):
                return 27
            elif x == r_ulonglong(27):
                return 3
            return 0
        fn = self.getcompiled(f, [r_ulonglong])
        for x in (0,1,2,3,9,27,48, r_ulonglong(-9)):
            assert fn(r_ulonglong(x)) == f(r_ulonglong(x))

    def test_chr_switch(self):
        def f(y):
            x = chr(y)
            if x == 'a':
                return 'b'
            elif x == 'b':
                return 'c'
            elif x == 'c':
                return 'd'
            return '@'
        fn = self.getcompiled(f, [int])
        for x in 'ABCabc@':
            y = ord(x)
            assert fn(y) == f(y)

    def test_char_may_be_signed(self):
        def f(n):
            case = chr(n)
            if case == '\xFF': return 1
            if case == '\xFE': return 2
            if case == '\xFD': return 3
            if case == '\xFC': return 4
            if case == '\xFB': return 5
            if case == '\xFA': return 6
            return 7
        fn = self.getcompiled(f, [int])
        for input, expected in [(255, 1), (253, 3), (251, 5), (161, 7)]:
            res = fn(input)
            assert res == expected

    def test_unichr_switch(self):
        def f(y):
            x = unichr(y)
            if x == u'a':
                return 'b'
            elif x == u'b':
                return 'c'
            elif x == u'c':
                return 'd'
            return '@'
        fn = self.getcompiled(f, [int])
        for x in u'ABCabc@':
            y = ord(x)
            assert fn(y) == f(y)


class TestTypedOptimizedRaisingOps:
    def getcompiled(self, func, argtypes):
        return compile(func, argtypes)

    def test_int_floordiv_zer(self):
        def f(x):
            try:
                y = 123 / x
            except:
                y = 456
            return y
        fn = self.getcompiled(f, [int])
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)

    def test_ovf_op_in_loop(self):
        # This checks whether the raising operations are implemented using
        # unsigned arithmetic. The problem with using signed arithmetic is that
        # signed overflow is undefined in C and the optimizer is allowed to
        # remove the overflow check.
        from sys import maxint
        from rpython.rlib.rarithmetic import ovfcheck
        def f(x, y):
            ret = 0
            for i in range(y):
                try:
                    ret = ovfcheck(x + i)
                except OverflowError:
                    break
            return ret
        fc = self.getcompiled(f, [int, int])
        assert fc(10, 10) == 19
        assert fc(maxint, 10) == maxint
