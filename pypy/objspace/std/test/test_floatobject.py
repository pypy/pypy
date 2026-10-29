import pytest

from pypy.objspace.std.floatobject import W_FloatObject, _remove_underscores
from pypy.objspace.std.intobject import W_IntObject


class TestW_FloatObject:
    def test_pow_fff(self):
        x = 10.0
        y = 2.0
        z = 13.0
        f1 = W_FloatObject(x)
        f2 = W_FloatObject(y)
        f3 = W_FloatObject(z)
        self.space.raises_w(self.space.w_TypeError,
                            f1.descr_pow,
                            self.space, f2, f3)

    def test_pow_ffn(self):
        x = 10.0
        y = 2.0
        f1 = W_FloatObject(x)
        f2 = W_FloatObject(y)
        v = f1.descr_pow(self.space, f2, self.space.w_None)
        assert v.floatval == x ** y
        f1 = W_FloatObject(-1.23)
        f2 = W_FloatObject(-4.56)
        v = f1.descr_pow(self.space, f2, self.space.w_None)
        assert self.space.isinstance_w(v, self.space.w_complex)
        x = -10
        y = 2.0
        f1 = W_FloatObject(x)
        f2 = W_FloatObject(y)
        v = f1.descr_pow(self.space, f2, self.space.w_None)
        assert v.floatval == x**y

    def test_dont_use_long_impl(self):
        from pypy.objspace.std.longobject import W_LongObject
        space = self.space
        saved = W_LongObject.__dict__['fromfloat']
        W_LongObject.fromfloat = lambda space, x: disabled
        try:
            w_i = space.wrap(12)
            w_f = space.wrap(12.3)
            assert space.unwrap(space.eq(w_f, w_i)) is False
            assert space.unwrap(space.eq(w_i, w_f)) is False
            assert space.unwrap(space.ne(w_f, w_i)) is True
            assert space.unwrap(space.ne(w_i, w_f)) is True
            assert space.unwrap(space.lt(w_f, w_i)) is False
            assert space.unwrap(space.lt(w_i, w_f)) is True
            assert space.unwrap(space.le(w_f, w_i)) is False
            assert space.unwrap(space.le(w_i, w_f)) is True
            assert space.unwrap(space.gt(w_f, w_i)) is True
            assert space.unwrap(space.gt(w_i, w_f)) is False
            assert space.unwrap(space.ge(w_f, w_i)) is True
            assert space.unwrap(space.ge(w_i, w_f)) is False
        finally:
            W_LongObject.fromfloat = saved

    def test_remove_undercores(self):
        valid = [
            '0_0_0',
            '4_2',
            '1_0000_0000',
            '0b1001_0100',
            '0o5_7_7',
            '1_00_00.5',
            '1_00_00.5e5',
            '1_00_00e5_1',
            '1e1_0',
            '.1_4',
            '.1_4e1',
            '1_00_00j',
            '1_00_00.5j',
            '1_00_00e5_1j',
            '.1_4j',
            '(1_2.5+3_3j)',
            '(.5_6j)',
        ]
        for s in valid:
            assert _remove_underscores(s) == s.replace("_", "")

        invalid = [
            # Trailing underscores:
            '0_',
            '42_',
            '1.4j_',
            # Multiple consecutive underscores:
            '4_______2',
            '0.1__4',
            '0.1__4j',
            '0b1001__0100',
            '0xffff__ffff',
            '0x___',
            '0o5__77',
            '1e1__0',
            '1e1__0j',
            # Underscore right before a dot:
            '1_.4',
            '1_.4j',
            # Underscore right after a dot:
            '1._4',
            '1._4j',
            '._5',
            '._5j',
            # Underscore right after a sign:
            '1.0e+_1',
            '1.0e+_1j',
            # Underscore right before j:
            '1.4_j',
            '1.4e5_j',
            # Underscore right before e:
            '1_e1',
            '1.4_e1',
            '1.4_e1j',
            # Underscore right after e:
            '1e_1',
            '1.4e_1',
            '1.4e_1j',
            # Complex cases with parens:
            '(1+1.5_j_)',
            '(1+1.5_j)',
        ]
        for s in invalid:
            pytest.raises(ValueError, _remove_underscores, s)


def test_avoid_bigints(space):
    w_f = space.newfloat(123.456)
    assert isinstance(w_f.descr_trunc(space), W_IntObject)
    assert isinstance(w_f.descr___round__(space), W_IntObject)
