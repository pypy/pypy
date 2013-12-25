import py
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.jit import JitDriver


class TestByteArray(LLJitMixin):

    def test_getitem(self):
        x = bytearray("foobar")
        def fn(n):
            return x[n]
        res = self.interp_operations(fn, [3])
        assert res == ord('b')

    def test_len(self):
        x = bytearray("foobar")
        def fn(n):
            return len(x)
        res = self.interp_operations(fn, [3])
        assert res == 6

    def test_setitem(self):
        x = bytearray("foobar")
        def fn(n):
            x[n] = 3
            return x[3] + 1000 * x[4]

        res = self.interp_operations(fn, [3])
        assert res == 3 + 1000 * ord('a')

    def test_new_bytearray(self):
        def fn(n, m):
            x = bytearray(str(n))
            x[m] = 4
            return int(str(x))

        res = self.interp_operations(fn, [610978, 3])
        assert res == 610478

    def test_slice(self):
        def fn(n):
            x = bytearray(str(n))
            x = x[1:5]
            x[m] = 5
            return int(str(x))
        res = self.interp_operations(fn, [610978, 1])
        assert res == 1597
