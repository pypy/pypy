# encoding: utf-8
import pytest
import sys
from pypy.interpreter.error import OperationError
from pypy.objspace.std import intobject as iobj
from rpython.rlib.rarithmetic import r_uint, is_valid_int, intmask
from rpython.rlib.rbigint import rbigint, LONG_BIT, SUPPORT_INT128

from rpython.jit.metainterp.test.support import LLJitMixin, noConst

from hypothesis import given, strategies

class TestW_IntObject:

    def _longshiftresult(self, x):
        """ calculate an overflowing shift """
        n = 1
        l = long(x)
        while 1:
            ires = x << n
            lres = l << n
            if not is_valid_int(ires) or lres != ires:
                return n
            n += 1

    def test_int_w(self):
        assert self.space.int_w(self.space.wrap(42)) == 42

    def test_uint_w(self):
        space = self.space
        assert space.uint_w(space.wrap(42)) == 42
        assert isinstance(space.uint_w(space.wrap(42)), r_uint)
        space.raises_w(space.w_ValueError, space.uint_w, space.wrap(-1))

    def test_bigint_w(self):
        space = self.space
        assert isinstance(space.bigint_w(space.wrap(42)), rbigint)
        assert space.bigint_w(space.wrap(42)).eq(rbigint.fromint(42))

    def test_repr(self):
        x = 1
        f1 = iobj.W_IntObject(x)
        result = f1.descr_repr(self.space)
        assert self.space.unwrap(result) == repr(x)

    def test_str(self):
        x = 12345
        f1 = iobj.W_IntObject(x)
        result = f1.descr_str(self.space)
        assert self.space.unwrap(result) == str(x)

    def test_hash(self):
        x = 42
        f1 = iobj.W_IntObject(x)
        result = f1.descr_hash(self.space)
        assert result.intval == hash(x)

    def test_compare(self):
        import operator
        optab = ['lt', 'le', 'eq', 'ne', 'gt', 'ge']
        for x in (-10, -1, 0, 1, 2, 1000, sys.maxint):
            for y in (-sys.maxint-1, -11, -9, -2, 0, 1, 3, 1111, sys.maxint):
                for op in optab:
                    wx = iobj.W_IntObject(x)
                    wy = iobj.W_IntObject(y)
                    res = getattr(operator, op)(x, y)
                    method = getattr(wx, 'descr_%s' % op)
                    myres = method(self.space, wy)
                    assert self.space.unwrap(myres) == res

    def test_add(self):
        space = self.space
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        result = f1.descr_add(space, f2)
        assert result.intval == x+y
        x = sys.maxint
        y = 1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_add(space, f2)
        assert space.isinstance_w(v, space.w_int)
        assert space.bigint_w(v).eq(rbigint.fromlong(x + y))

    def test_add_ovf_int_op_shortcut(self, monkeypatch):
        from pypy.objspace.std.longobject import W_LongObject, rbigint
        monkeypatch.setattr(W_LongObject, 'fromint', None)

        space = self.space
        x = sys.maxint
        y = 1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_add(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(x + y))

    def test_lt_int_long_no_conversion(self, monkeypatch):
        from pypy.objspace.std.longobject import W_LongObject, rbigint

        space = self.space
        x = sys.maxint
        y = 1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y).as_w_long(space)

        monkeypatch.setattr(iobj.W_IntObject, 'as_w_long', None)
        v = f1.descr_gt(space, f2) # does *not* convert f1 to a bigint
        assert space.is_true(v)

    def test_mul_int_long_no_conversion(self, monkeypatch):
        from pypy.objspace.std.longobject import W_LongObject, rbigint

        space = self.space
        x = sys.maxint
        y = 1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y).as_w_long(space)

        monkeypatch.setattr(iobj.W_IntObject, 'as_w_long', None)
        v = f1.descr_mul(space, f2) # does *not* convert f1 to a bigint

    def test_sub(self):
        space = self.space
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        result = f1.descr_sub(space, f2)
        assert result.intval == x-y
        x = sys.maxint
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_sub(space, f2)
        assert space.isinstance_w(v, space.w_int)
        assert space.bigint_w(v).eq(rbigint.fromlong(sys.maxint - -1))

    def test_sub_ovf_int_op_shortcut(self, monkeypatch):
        from pypy.objspace.std.longobject import W_LongObject, rbigint
        monkeypatch.setattr(W_LongObject, 'fromint', None)

        space = self.space
        x = sys.maxint
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_sub(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(x - y))

    def test_mul(self):
        space = self.space
        x = 2
        y = 3
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        result = f1.descr_mul(space, f2)
        assert result.intval == x*y
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_mul(space, f2)
        assert space.isinstance_w(v, space.w_int)
        assert space.bigint_w(v).eq(rbigint.fromlong(x * y))
        x = sys.maxint // 4
        y = sys.maxint // 8
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_mul(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(x * y))

    def test_mod(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_mod(self.space, f2)
        assert v.intval == x % y
        # not that mod cannot overflow

    def test_divmod(self):
        space = self.space
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        ret = f1.descr_divmod(space, f2)
        v, w = space.unwrap(ret)
        assert (v, w) == divmod(x, y)
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_divmod(space, f2)
        w_q, w_r = space.fixedview(v, 2)
        assert space.isinstance_w(w_q, space.w_int)
        expected = divmod(x, y)
        assert space.bigint_w(w_q).eq(rbigint.fromlong(expected[0]))
        # no overflow possible
        assert space.unwrap(w_r) == expected[1]

    def test_pow_iii(self):
        x = 10
        y = 2
        z = 13
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        f3 = iobj.W_IntObject(z)
        v = f1.descr_pow(self.space, f2, f3)
        assert v.intval == pow(x, y, z)
        f1, f2, f3 = [iobj.W_IntObject(i) for i in (10, -1, 42)]
        self.space.raises_w(self.space.w_ValueError,
                            f1.descr_pow, self.space, f2, f3)
        f1, f2, f3 = [iobj.W_IntObject(i) for i in (10, 5, 0)]
        self.space.raises_w(self.space.w_ValueError,
                            f1.descr_pow, self.space, f2, f3)

    def test_pow_iin(self):
        space = self.space
        x = 10
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_pow(space, f2, space.w_None)
        assert v.intval == x ** y
        f1, f2 = [iobj.W_IntObject(i) for i in (10, 20)]
        v = f1.descr_pow(space, f2, space.w_None)
        assert space.isinstance_w(v, space.w_int)
        assert space.bigint_w(v).eq(rbigint.fromlong(pow(10, 20)))

    def test_pow_ovf_without_fromint(self, monkeypatch):
        space = self.space
        orig = rbigint.fromint
        def fromint(x):
            assert x == sys.maxint // 4 # it's not called for 16
            return orig(x)
        monkeypatch.setattr(rbigint, 'fromint', staticmethod(fromint))
        x = sys.maxint // 4
        y = 16
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_pow(space, f2)
        assert space.bigint_w(v).eq(rbigint.fromlong(x ** y))


    try:
        from hypothesis import given, strategies, example
    except ImportError:
        pass
    else:
        @given(
           a=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint),
           b=strategies.integers(min_value=0, max_value=sys.maxint),
           c=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint))
        @example(0, 0, -sys.maxint-1)
        @example(0, 1, -sys.maxint-1)
        @example(1, 0, -sys.maxint-1)
        def test_hypot_pow(self, a, b, c):
            if c == 0:
                return
            #
            # "pow(a, b, c)": if b < 0, should get an app-level ValueError.
            # Otherwise, should always work except if c == -maxint-1
            if b < 0:
                expected = "app-level ValueError"
            elif b > 0 and c == -sys.maxint-1:
                expected = OverflowError
            else:
                expected = pow(a, b, c)

            try:
                result = iobj._pow(self.space, a, b, c)
            except OperationError as e:
                assert ('ValueError: pow() 2nd argument cannot be negative '
                        'when 3rd argument specified' == e.errorstr(self.space))
                result = "app-level ValueError"
            except OverflowError:
                result = OverflowError
            assert result == expected

            # check exponent -1
            if isinstance(expected, int):
                try:
                    result = iobj._pow(self.space, a, -1, c)
                except OperationError as e:
                    pass
                except OverflowError:
                    pass
                else:
                    assert (a * result % c) == 1 % c


        @given(
           a=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint),
           b=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint))
        def test_hypot_pow_nomod(self, a, b):
            # "a ** b": detect overflows and ValueErrors
            if b < 0:
                expected = ValueError
            elif b > 128 and not (-1 <= a <= 1):
                expected = OverflowError
            else:
                expected = a ** b
                if expected != intmask(expected):
                    expected = OverflowError

            try:
                result = iobj._pow(self.space, a, b, 0)
            except ValueError:
                result = ValueError
            except OverflowError:
                result = OverflowError
            assert result == expected

    def test_neg(self):
        space = self.space
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_neg(space)
        assert v.intval == -x
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(x)
        v = f1.descr_neg(space)
        assert space.isinstance_w(v, space.w_int)
        assert space.bigint_w(v).eq(rbigint.fromlong(-x))

    def test_pos(self):
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_pos(self.space)
        assert v.intval == +x
        x = -42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_pos(self.space)
        assert v.intval == +x

    def test_abs(self):
        space = self.space
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_abs(space)
        assert v.intval == abs(x)
        x = -42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_abs(space)
        assert v.intval == abs(x)
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(x)
        v = f1.descr_abs(space)
        assert space.isinstance_w(v, space.w_int)
        assert space.bigint_w(v).eq(rbigint.fromlong(abs(x)))

    def test_invert(self):
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_invert(self.space)
        assert v.intval == ~x

    def test_lshift(self):
        space = self.space
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_lshift(space, f2)
        assert v.intval == x << y
        y = self._longshiftresult(x)
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_lshift(space, f2)
        assert space.isinstance_w(v, space.w_int)
        assert space.bigint_w(v).eq(rbigint.fromlong(x << y))

    def test_lshift_without_fromint(self, monkeypatch):
        if LONG_BIT != 64 or not SUPPORT_INT128:
            pytest.skip("64-bit only speedup, and only if the C compiler "
                        "supports __int128 (e.g. not on MSVC/Windows)")
        space = self.space
        monkeypatch.setattr(rbigint, 'fromint', None)
        x = sys.maxint // 4
        y = 16
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_lshift(space, f2)
        assert space.bigint_w(v).eq(rbigint.fromlong(x << y))

    def test_rshift(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_rshift(self.space, f2)
        assert v.intval == x >> y

    def test_and(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_and(self.space, f2)
        assert v.intval == x & y

    def test_xor(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_xor(self.space, f2)
        assert v.intval == x ^ y

    def test_or(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_or(self.space, f2)
        assert v.intval == x | y

    def test_int(self):
        f1 = iobj.W_IntObject(1)
        result = f1.int(self.space)
        assert result == f1

class AppTestInt(object):
    def test_base_range_checked_before_value_type(self):
        # CPython's long_new_impl validates the base range before it dispatches
        # on the type of the first argument.
        raises(ValueError, int, None, 1)
        raises(ValueError, int, None, -35)
        raises(ValueError, int, None, 37)
        raises(ValueError, int, [], 1)
        raises(ValueError, int, '10', 1)
        raises(TypeError, int, None, 10)
        assert int('10', 2) == 2
        assert int('ff', 16) == 255
        assert int('10', 0) == 10

    def test_hash(self):
        assert hash(-1) == (-1).__hash__() == -2
        assert hash(-2) == (-2).__hash__() == -2

    def test_conjugate(self):
        assert (1).conjugate() == 1
        assert (-1).conjugate() == -1

        class I(int):
            pass
        assert I(1).conjugate() == 1

        class I(int):
            def __pos__(self):
                return 42
        assert I(1).conjugate() == 1

    def test_inplace(self):
        a = 1
        a += 1
        assert a == 2
        a -= 1
        assert a == 1
        e = raises(TypeError, "a += 'aa'")
        assert "+=" in str(e.value)

    def test_shift_zeros(self):
        assert (1 << 0) == 1
        assert (1 >> 0) == 1

    def test_overflow(self):
        import sys
        n = sys.maxsize + 1
        assert isinstance(n, int)

    def test_pow(self):
        assert pow(2, -10) == 1/1024.

    def test_int_subclass_ops(self):
        import sys
        class j(int):
            def __add__(self, other):
                return "add."
            def __iadd__(self, other):
                return "iadd."
            def __sub__(self, other):
                return "sub."
            def __isub__(self, other):
                return "isub."
            def __mul__(self, other):
                return "mul."
            def __imul__(self, other):
                return "imul."
            def __lshift__(self, other):
                return "lshift."
            def __ilshift__(self, other):
                return "ilshift."
        assert j(100) +  5   == "add."
        assert j(100) +  str == "add."
        assert j(100) -  5   == "sub."
        assert j(100) -  str == "sub."
        assert j(100) *  5   == "mul."
        assert j(100) *  str == "mul."
        assert j(100) << 5   == "lshift."
        assert j(100) << str == "lshift."
        assert (5 +  j(100),  type(5 +  j(100))) == (     105, int)
        assert (5 -  j(100),  type(5 -  j(100))) == (     -95, int)
        assert (5 *  j(100),  type(5 *  j(100))) == (     500, int)
        assert (5 << j(100),  type(5 << j(100))) == (5 << 100, int)
        assert (j(100) >> 2,  type(j(100) >> 2)) == (      25, int)

    def test_truediv(self):
        import operator
        x = 1000000
        a = x / 2
        assert a == 500000
        a = operator.truediv(x, 2)
        assert a == 500000.0

        x = 63050394783186940
        a = x / 7
        assert a == 9007199254740991
        a = operator.truediv(x, 7)
        assert a == 9007199254740991.0

    def test_truediv_future(self):
        ns = dict(x=63050394783186940)
        exec("from __future__ import division; import operator; "
             "a = x / 7; b = operator.truediv(x, 7)", ns)
        assert ns['a'] == 9007199254740991.0
        assert ns['b'] == 9007199254740991.0

    def test_binop_overflow(self):
        x = int(2)
        assert x.__lshift__(128) == 680564733841876926926749214863536422912

    def test_rbinop_overflow(self):
        x = int(321)
        assert x.__rlshift__(333) == 1422567365923326114875084456308921708325401211889530744784729710809598337369906606315292749899759616

    def test_some_rops(self):
        b = 2 ** 31
        x = -b
        assert x.__rsub__(2) == (2 + b)

    def test_pow_negative_exponent_mod(self):
        import math
        for i in range(1, 7):
            for j in range(2, 7):
                for sign in [1, -1]:
                    i = i * sign
                    if math.gcd(i, j) != 1:
                        with raises(ValueError):
                            pow(i, -1, j)
                        continue
                    x = pow(i, -1, j)
                    assert (x * i) % j == 1 % j

                    for k in range(2, 4):
                        y = pow(i, -k, j)
                        assert y == pow(x, k, j)

    def test_rpow_bug(self):
        assert (1).__rpow__(2 ** 100) == 2 ** 100


def test_hash_examples():
    for i in range(1000):
        assert iobj._hash_int(i) == i
        assert iobj._hash_int(-i-2) == -i-2
    assert iobj._hash_int(-1) == -2

    # now bigger/smaller than HASH_MODULUS
    for i in range(1000):
        input = iobj.HASH_MODULUS + i
        assert iobj._hash_int(input) == i

        input = -iobj.HASH_MODULUS-i-1
        if -i-1 == -1:
            assert iobj._hash_int(input) == -2
        else:
            assert iobj._hash_int(input) == -i-1
    if sys.maxsize > 2**31 - 1:
        assert iobj._hash_int(-sys.maxsize-1) == -4
    else:
        assert iobj._hash_int(-sys.maxsize-1) == -2

@given(strategies.integers(min_value=-sys.maxsize-1, max_value=sys.maxsize))
def test_agreement_rbigint_hash(x):
    from pypy.objspace.std.longobject import _hash_long
    assert iobj._hash_int(x) == _hash_long(rbigint.fromint(x))
    
class TestHashNoBranch(LLJitMixin):
    def test_int_hash_no_guards(self):
        res = self.interp_operations(iobj._hash_int, [123])
        assert res == 123
        self.check_operations_history(guard_true=0, guard_false=0)


class AppTestIntShortcut(AppTestInt):
    spaceconfig = {"objspace.std.intshortcut": True}

    def test_inplace(self):
        # ensure other inplace ops still work
        l = []
        l += range(5)
        assert l == list(range(5))
        a = 8.5
        a -= .5
        assert a == 8
