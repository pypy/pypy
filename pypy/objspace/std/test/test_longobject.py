# -*- encoding: utf-8 -*-
from pypy.objspace.std import longobject as lobj
from rpython.rlib.rbigint import rbigint

class TestW_LongObject:
    def test_bigint_w(self):
        space = self.space
        fromlong = lobj.W_LongObject.fromlong
        assert isinstance(space.bigint_w(fromlong(42)), rbigint)
        assert space.bigint_w(fromlong(42)).eq(rbigint.fromint(42))
        assert space.bigint_w(fromlong(-1)).eq(rbigint.fromint(-1))
        w_obj = space.wrap("hello world")
        space.raises_w(space.w_TypeError, space.bigint_w, w_obj)
        w_obj = space.wrap(123.456)
        space.raises_w(space.w_TypeError, space.bigint_w, w_obj)

        w_obj = fromlong(42)
        assert space.unwrap(w_obj) == 42

    def test_overflow_error(self):
        space = self.space
        fromlong = lobj.W_LongObject.fromlong
        w_big = fromlong(10**900)
        space.raises_w(space.w_OverflowError, space.float_w, w_big)

    def test_rint_variants(self):
        from rpython.rtyper.tool.rfficache import platform
        space = self.space
        for r in platform.numbertype_to_rclass.values():
            if r is int:
                continue
            print r
            values = [0, -1, r.MASK>>1, -(r.MASK>>1)-1]
            for x in values:
                if not r.SIGNED:
                    x &= r.MASK
                w_obj = space.newlong_from_rarith_int(r(x))
                assert space.bigint_w(w_obj).eq(rbigint.fromlong(x))
