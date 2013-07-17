

class AppTestIntOp:
    spaceconfig = dict(usemodules=['__pypy__'])

    def w_intmask(self, n):
        import sys
        n &= (sys.maxint*2+1)
        if n > sys.maxint:
            n -= 2*(sys.maxint+1)
        return int(n)

    def test_intmask(self):
        import sys
        assert self.intmask(sys.maxint) == sys.maxint
        assert self.intmask(sys.maxint+1) == -sys.maxint-1
        assert self.intmask(-sys.maxint-2) == sys.maxint
        N = 2 ** 128
        assert self.intmask(N+sys.maxint) == sys.maxint
        assert self.intmask(N+sys.maxint+1) == -sys.maxint-1
        assert self.intmask(N-sys.maxint-2) == sys.maxint

    def test_int_add(self):
        import sys
        from __pypy__ import intop
        assert intop.int_add(40, 2) == 42
        assert intop.int_add(sys.maxint, 1) == -sys.maxint-1
        assert intop.int_add(-2, -sys.maxint) == sys.maxint

    def test_int_sub(self):
        import sys
        from __pypy__ import intop
        assert intop.int_sub(40, -2) == 42
        assert intop.int_sub(sys.maxint, -1) == -sys.maxint-1
        assert intop.int_sub(-2, sys.maxint) == sys.maxint

    def test_int_mul(self):
        import sys
        from __pypy__ import intop
        assert intop.int_mul(40, -2) == -80
        assert intop.int_mul(-sys.maxint, -sys.maxint) == (
            self.intmask(sys.maxint ** 2))

    def test_int_floordiv(self):
        import sys
        from __pypy__ import intop
        assert intop.int_floordiv(41, 3) == 13
        assert intop.int_floordiv(41, -3) == -13
        assert intop.int_floordiv(-41, 3) == -13
        assert intop.int_floordiv(-41, -3) == 13
        assert intop.int_floordiv(-sys.maxint, -1) == sys.maxint
        assert intop.int_floordiv(sys.maxint, -1) == -sys.maxint

    def test_int_mod(self):
        import sys
        from __pypy__ import intop
        assert intop.int_mod(41, 3) == 2
        assert intop.int_mod(41, -3) == 2
        assert intop.int_mod(-41, 3) == -2
        assert intop.int_mod(-41, -3) == -2
        assert intop.int_mod(-sys.maxint, -1) == 0
        assert intop.int_mod(sys.maxint, -1) == 0

    def test_int_lshift(self):
        import sys
        from __pypy__ import intop
        if sys.maxint == 2**31-1:
            bits = 32
        else:
            bits = 64
        assert intop.int_lshift(42, 3) == 42 << 3
        assert intop.int_lshift(0, 3333) == 0
        assert intop.int_lshift(1, bits-2) == 1 << (bits-2)
        assert intop.int_lshift(1, bits-1) == -sys.maxint-1 == (-1) << (bits-1)
        assert intop.int_lshift(-1, bits-2) == (-1) << (bits-2)
        assert intop.int_lshift(-1, bits-1) == -sys.maxint-1
        assert intop.int_lshift(sys.maxint // 3, 2) == (
            self.intmask((sys.maxint // 3) << 2))
        assert intop.int_lshift(-sys.maxint // 3, 2) == (
            self.intmask((-sys.maxint // 3) << 2))

    def test_uint_rshift(self):
        import sys
        from __pypy__ import intop
        if sys.maxint == 2**31-1:
            bits = 32
        else:
            bits = 64
        N = 1 << bits
        assert intop.uint_rshift(42, 3) == 42 >> 3
        assert intop.uint_rshift(-42, 3) == (N-42) >> 3
        assert intop.uint_rshift(0, 3333) == 0
        assert intop.uint_rshift(-1, 0) == -1
        assert intop.uint_rshift(-1, 1) == sys.maxint
        assert intop.uint_rshift(-1, bits-2) == 3
        assert intop.uint_rshift(-1, bits-1) == 1
