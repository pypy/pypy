import sys, operator
from pypy.translator.translator import TranslationContext
from pypy.annotation import model as annmodel
from pypy.rpython.test import snippet
from pypy.rlib.rarithmetic import r_int, r_uint, r_longlong, r_ulonglong
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

class TestSnippet(object):

    def _test(self, func, types):
        t = TranslationContext()
        t.buildannotator().build_types(func, types)
        t.buildrtyper().specialize()
        t.checkgraphs()    
     
    def test_not1(self):
        self._test(snippet.not1, [int])

    def test_not2(self):
        self._test(snippet.not2, [int])

    def test_int1(self):
        self._test(snippet.int1, [int])

    def test_int_cast1(self):
        self._test(snippet.int_cast1, [int])

    def DONTtest_unary_operations(self):
        # XXX TODO test if all unary operations are implemented
        for opname in annmodel.UNARY_OPERATIONS:
            print 'UNARY_OPERATIONS:', opname

    def DONTtest_binary_operations(self):
        # XXX TODO test if all binary operations are implemented
        for opname in annmodel.BINARY_OPERATIONS:
            print 'BINARY_OPERATIONS:', opname


class BaseTestRint(BaseRtypingTest):
    
    def test_char_constant(self):
        def dummyfn(i):
            return chr(i)
        res = self.interpret(dummyfn, [ord(' ')])
        assert res == ' '
        res = self.interpret(dummyfn, [0])
        assert res == '\0'
        res = self.interpret(dummyfn, [ord('a')])
        assert res == 'a'

    def test_str_of_int(self):
        def dummy(i):
            return str(i)

        res = self.interpret(dummy, [0])
        assert self.ll_to_string(res) == '0'

        res = self.interpret(dummy, [1034])
        assert self.ll_to_string(res) == '1034'

        res = self.interpret(dummy, [-123])
        assert self.ll_to_string(res) == '-123'

        res = self.interpret(dummy, [-sys.maxint-1])
        assert self.ll_to_string(res) == str(-sys.maxint-1)

    def test_hex_of_int(self):
        def dummy(i):
            return hex(i)

        res = self.interpret(dummy, [0])
        assert self.ll_to_string(res) == '0x0'

        res = self.interpret(dummy, [1034])
        assert self.ll_to_string(res) == '0x40a'

        res = self.interpret(dummy, [-123])
        assert self.ll_to_string(res) == '-0x7b'

        res = self.interpret(dummy, [-sys.maxint-1])
        res = self.ll_to_string(res)
        assert res == '-0x8' + '0' * (len(res)-4)

    def test_oct_of_int(self):
        def dummy(i):
            return oct(i)

        res = self.interpret(dummy, [0])
        assert self.ll_to_string(res) == '0'

        res = self.interpret(dummy, [1034])
        assert self.ll_to_string(res) == '02012'

        res = self.interpret(dummy, [-123])
        assert self.ll_to_string(res) == '-0173'

        res = self.interpret(dummy, [-sys.maxint-1])
        res = self.ll_to_string(res)
        assert res == '-' + oct(sys.maxint+1).replace('L', '').replace('l', '')

    def test_unsigned(self):
        bigvalue = sys.maxint + 17
        def dummy(i):
            i = r_uint(i)
            j = r_uint(bigvalue)
            return i < j

        res = self.interpret(dummy,[0])
        assert res is True

        res = self.interpret(dummy, [-1])
        assert res is False    # -1 ==> 0xffffffff

    def test_specializing_int_functions(self):
        def f(i):
            return i + 1
        f._annspecialcase_ = "specialize:argtype(0)"
        def g(n):
            if n > 0:
                return f(r_longlong(0))
            else:
                return f(0)
        res = self.interpret(g, [0])
        assert res == 1

        res = self.interpret(g, [1])
        assert res == 1

    def test_downcast_int(self):
        def f(i):
            return int(i)
        res = self.interpret(f, [r_longlong(0)])
        assert res == 0

    def test_isinstance_vs_int_types(self):
        class FakeSpace(object):
            def wrap(self, x):
                if x is None:
                    return [None]
                if isinstance(x, str):
                    return x
                if isinstance(x, r_longlong):
                    return int(x)
                return "XXX"
            wrap._annspecialcase_ = 'specialize:argtype(0)'

        space = FakeSpace()
        def wrap(x):
            return space.wrap(x)
        res = self.interpret(wrap, [r_longlong(0)])
        assert res == 0

    def test_truediv(self):
        import operator
        def f(n, m):
            return operator.truediv(n, m)
        res = self.interpret(f, [20, 4])
        assert type(res) is float
        assert res == 5.0

    def test_float_conversion(self):
        def f(ii):
            return float(ii)
        res = self.interpret(f, [r_longlong(100000000)])
        assert type(res) is float
        assert res == 100000000.
        res = self.interpret(f, [r_longlong(1234567890123456789)])
        assert type(res) is float
        assert self.float_eq(res, 1.2345678901234568e+18)

    def test_float_conversion_implicit(self):
        def f(ii):
            return 1.0 + ii
        res = self.interpret(f, [r_longlong(100000000)])
        assert type(res) is float
        assert res == 100000001.
        res = self.interpret(f, [r_longlong(1234567890123456789)])
        assert type(res) is float
        assert self.float_eq(res, 1.2345678901234568e+18)

    def test_rarithmetic(self):
        inttypes = [int, r_uint, r_longlong, r_ulonglong]
        for inttype in inttypes:
            c = inttype()
            def f():
                return c
            res = self.interpret(f, [])
            assert res == f()
            assert type(res) == inttype

        for inttype in inttypes:
            def f():
                return inttype(0)
            res = self.interpret(f, [])
            assert res == f()
            assert type(res) == inttype

        for inttype in inttypes:
            def f(x):
                return x
            res = self.interpret(f, [inttype(0)])
            assert res == f(inttype(0))
            assert type(res) == inttype

    def test_neg_abs_ovf(self):
        for op in (operator.neg, abs):
            def f(x):
                try:
                    return ovfcheck(op(x))
                except OverflowError:
                    return 0
            res = self.interpret(f, [-1])
            assert res == 1
            res = self.interpret(f, [int(-1<<(r_int.BITS-1))])
            assert res == 0

            res = self.interpret(f, [r_longlong(-1)])
            assert res == 1
            res = self.interpret(f, [r_longlong(-1)<<(r_longlong.BITS-1)])
            assert res == 0

    div_mod_iteration_count = 1000
    def test_div_mod(self):
        import random

        for inttype in (int, r_longlong):

            def d(x, y):
                return x/y

            for i in range(self.div_mod_iteration_count):
                x = inttype(random.randint(-100000, 100000))
                y = inttype(random.randint(-100000, 100000))
                if not y: continue
                res = self.interpret(d, [x, y])
                assert res == d(x, y)

            def m(x, y):
                return x%y

            for i in range(self.div_mod_iteration_count):
                x = inttype(random.randint(-100000, 100000))
                y = inttype(random.randint(-100000, 100000))
                if not y: continue
                res = self.interpret(m, [x, y])
                assert res == m(x, y)

    def test_protected_div_mod(self):
        def div_unpro(x, y):
            return x//y
        def div_ovf(x, y):
            try:
                return ovfcheck(x//y)
            except OverflowError:
                return 42
        def div_zer(x, y):
            try:
                return x//y
            except ZeroDivisionError:
                return 84
        def div_ovf_zer(x, y):
            try:
                return ovfcheck(x//y)
            except OverflowError:
                return 42
            except ZeroDivisionError:
                return 84

        def mod_unpro(x, y):
            return x%y
        def mod_ovf(x, y):
            try:
                return ovfcheck(x%y)
            except OverflowError:
                return 42
        def mod_zer(x, y):
            try:
                return x%y
            except ZeroDivisionError:
                return 84
        def mod_ovf_zer(x, y):
            try:
                return ovfcheck(x%y)
            except OverflowError:
                return 42
            except ZeroDivisionError:
                return 84

        for inttype in (int, r_longlong):

            args = [( 5, 2), (-5, 2), ( 5,-2), (-5,-2),
                    ( 6, 2), (-6, 2), ( 6,-2), (-6,-2),
                    (-sys.maxint, -1), (4, 0)]

            funcs = [div_unpro, div_ovf, div_zer, div_ovf_zer,
                     mod_unpro, mod_ovf, mod_zer, mod_ovf_zer]

            for func in funcs:
                print func
                if 'ovf' in func.func_name and inttype is r_longlong:
                    continue # don't have many llong_*_ovf operations...
                for x, y in args:
                    x, y = inttype(x), inttype(y)
                    try:
                        res1 = ovfcheck(func(x, y))
                    except (OverflowError, ZeroDivisionError):
                        continue
                    res2 = self.interpret(func, [x, y])
                    assert res1 == res2

    def test_int_add_nonneg_ovf(self):
        def f(x):
            try:
                a = ovfcheck(x + 50)
            except OverflowError:
                return 0
            try:
                a += ovfcheck(100 + x)
            except OverflowError:
                return 1
            return a
        res = self.interpret(f, [-3])
        assert res == 144
        res = self.interpret(f, [sys.maxint-50])
        assert res == 1
        res = self.interpret(f, [sys.maxint])
        assert res == 0

class TestLLtype(BaseTestRint, LLRtypeMixin):
    pass

class TestOOtype(BaseTestRint, OORtypeMixin):
    pass
