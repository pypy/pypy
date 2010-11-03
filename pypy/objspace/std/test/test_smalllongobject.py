import py
import sys
from pypy.objspace.std.smalllongobject import W_SmallLongObject
from pypy.objspace.std.test import test_longobject
from pypy.conftest import gettestobjspace
from pypy.rlib.rarithmetic import r_longlong
from pypy.interpreter.error import OperationError


def test_direct():
    space = gettestobjspace(**{"objspace.std.withsmalllong": True})
    w5 = space.wrap(r_longlong(5))
    assert isinstance(w5, W_SmallLongObject)
    wlarge = space.wrap(r_longlong(0x123456789ABCDEFL))
    #
    assert space.int_w(w5) == 5
    if sys.maxint < 0x123456789ABCDEFL:
        py.test.raises(OperationError, space.int_w, wlarge)
    else:
        assert space.int_w(wlarge) == 0x123456789ABCDEF
    #
    assert space.pos(w5) is w5
    assert space.abs(w5) is w5
    wm5 = space.wrap(r_longlong(-5))
    assert space.int_w(space.abs(wm5)) == 5
    assert space.int_w(space.neg(w5)) == -5
    assert space.is_true(w5) is True
    assert space.is_true(wm5) is True
    w0 = space.wrap(r_longlong(0))
    assert space.is_true(w0) is False
    #
    w14000000000000 = space.wrap(r_longlong(0x14000000000000L))
    assert space.is_true(space.eq(
        space.lshift(w5, space.wrap(49)), w14000000000000)) is False
    assert space.is_true(space.eq(
        space.lshift(w5, space.wrap(50)), w14000000000000)) is True
    #
    w_huge = space.sub(space.lshift(w5, space.wrap(150)), space.wrap(1))
    wx = space.and_(w14000000000000, w_huge)
    assert space.is_true(space.eq(wx, w14000000000000))


class AppTestSmallLong(test_longobject.AppTestLong):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmalllong": True})

    def test_sl_simple(self):
        import __pypy__
        s = __pypy__.internal_repr(5L)
        assert 'SmallLong' in s

    def test_sl_hash(self):
        import __pypy__
        x = 5L
        assert 'SmallLong' in __pypy__.internal_repr(x)
        assert hash(5) == hash(x)
        biglong = 5L
        biglong ^= 2**100      # hack based on the fact that xor__Long_Long
        biglong ^= 2**100      # does not call newlong()
        assert biglong == 5L
        assert 'SmallLong' not in __pypy__.internal_repr(biglong)
        assert hash(5) == hash(biglong)
        #
        x = 0x123456789ABCDEFL
        assert 'SmallLong' in __pypy__.internal_repr(x)
        biglong = x
        biglong ^= 2**100
        biglong ^= 2**100
        assert biglong == x
        assert 'SmallLong' not in __pypy__.internal_repr(biglong)
        assert hash(biglong) == hash(x)

    def test_sl_int(self):
        x = 0x123456789ABCDEFL
        two = 2
        assert int(x) == x
        assert type(int(x)) == type(0x1234567 ** two)
        y = x >> 32
        assert int(y) == y
        assert type(int(y)) is int

    def test_sl_long(self):
        import __pypy__
        x = long(0)
        assert 'SmallLong' in __pypy__.internal_repr(x)

    def test_sl_add(self):
        import __pypy__
        x = 0x123456789ABCDEFL
        assert x + x == 0x2468ACF13579BDEL
        assert 'SmallLong' in __pypy__.internal_repr(x + x)
        x = -0x123456789ABCDEFL
        assert x + x == -0x2468ACF13579BDEL
        assert 'SmallLong' in __pypy__.internal_repr(x + x)
        x = 0x723456789ABCDEF0L
        assert x + x == 0xE468ACF13579BDE0L
        assert 'SmallLong' not in __pypy__.internal_repr(x + x)
        x = -0x723456789ABCDEF0L
        assert x + x == -0xE468ACF13579BDE0L
        assert 'SmallLong' not in __pypy__.internal_repr(x + x)

    def test_sl_add_32(self):
        import sys, __pypy__
        if sys.maxint == 2147483647:
            x = 2147483647
            assert x + x == 4294967294L
            assert 'SmallLong' in __pypy__.internal_repr(x + x)
            y = -1
            assert x - y == 2147483648L
            assert 'SmallLong' in __pypy__.internal_repr(x - y)

    def test_sl_lshift(self):
        for x in [1, 1L]:
            assert x << 1 == 2L
            assert x << 30 == 1073741824L
            assert x << 31 == 2147483648L
            assert x << 32 == 4294967296L
            assert x << 62 == 4611686018427387904L
            assert x << 63 == 9223372036854775808L
            assert x << 64 == 18446744073709551616L
            assert (x << 31) << 31 == 4611686018427387904L
            assert (x << 32) << 32 == 18446744073709551616L
