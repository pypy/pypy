import py, sys
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestMisc(BaseTestPyPyC):
    def test_f1(self):
        def f1(n):
            "Arbitrary test function."
            i = 0
            x = 1
            while i<n:
                j = 0
                while j<=i:
                    j = j + 1
                    x = x + (i&j)
                i = i + 1
            return x
        log = self.run(f1, [2117])
        assert log.result == 1083876708
        # we get two loops: in the initial one "i" is only read and thus is
        # not virtual, then "i" is written and thus we get a new loop where
        # "i" is virtual. However, in this specific case the two loops happen
        # to contain the very same operations
        loop0, loop1 = log.loops_by_filename(self.filepath)
        expected = """
            i9 = int_le(i7, i8)
            guard_true(i9, descr=...)
            i11 = int_add_ovf(i7, 1)
            guard_no_overflow(descr=...)
            i12 = int_and(i8, i11)
            i13 = int_add_ovf(i6, i12)
            guard_no_overflow(descr=...)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i13, i11, i8, descr=...)
        """
        assert loop0.match(expected)
        assert loop1.match(expected)

    def test_factorial(self):
        def fact(n):
            r = 1
            while n > 1:
                r *= n
                n -= 1
            return r
        log = self.run(fact, [7], threshold=5)
        assert log.result == 5040
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_gt(i4, 1)
            guard_true(i7, descr=...)
            i8 = int_mul_ovf(i5, i4)
            guard_no_overflow(descr=...)
            i10 = int_sub(i4, 1)
            --TICK--
            jump(p0, p1, p2, p3, i10, i8, descr=...)
        """)
        #
        log = self.run(fact, [25], threshold=20)
        assert log.result == 15511210043330985984000000L
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_gt(i4, 1)
            guard_true(i7, descr=...)
            p9 = call(ConstClass(fromint), i4, descr=...)
            guard_no_exception(descr=...)
            p11 = call(ConstClass(rbigint.mul), p5, p9, descr=...)
            guard_no_exception(descr=...)
            i13 = int_sub(i4, 1)
            --TICK--
            jump(p0, p1, p2, p3, i13, p11, descr=...)
        """)


    def test_mixed_type_loop(self):
        def main(n):
            i = 0.0
            j = 2
            while i < n:
                i = j + i
            return i
        #
        log = self.run(main, [1000])
        assert log.result == 1000.0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i9 = float_lt(f5, f7)
            guard_true(i9, descr=...)
            f10 = float_add(f8, f5)
            --TICK--
            jump(p0, p1, p2, p3, p4, f10, p6, f7, f8, descr=<Loop0>)
        """)


    def test_cached_pure_func_of_equal_fields(self):
        def main(n):
            class A(object):
                def __init__(self, val):
                    self.val1 = self.val2 = val
            a = A(1)
            b = A(1)
            sa = 0
            while n:
                sa += 2*a.val1
                sa += 2*b.val2
                b.val2 = a.val1
                n -= 1
            return sa
        #
        log = self.run(main, [1000])
        assert log.result == 4000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i12 = int_is_true(i4)
            guard_true(i12, descr=...)
            guard_not_invalidated(descr=...)
            i13 = int_add_ovf(i8, i9)
            guard_no_overflow(descr=...)
            i10p = getfield_gc_pure(p10, descr=...)
            i10 = int_mul_ovf(2, i10p)
            guard_no_overflow(descr=...)
            i14 = int_add_ovf(i13, i10)
            guard_no_overflow(descr=...)
            setfield_gc(p7, p11, descr=...)
            i17 = int_sub_ovf(i4, 1)
            guard_no_overflow(descr=...)
            --TICK--
            jump(..., descr=...)
            """)


    def test_range_iter(self):
        def main(n):
            def g(n):
                return range(n)
            s = 0
            for i in range(n):  # ID: for
                tmp = g(n)
                s += tmp[i]     # ID: getitem
                a = 0
            return s
        #
        log = self.run(main, [1000])
        assert log.result == 1000 * 999 / 2
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i16 = int_ge(i11, i12)
            guard_false(i16, descr=...)
            i17 = int_mul(i11, i14)
            i18 = int_add(i15, i17)
            i20 = int_add(i11, 1)
            i21 = force_token()
            setfield_gc(p4, i20, descr=<.* .*W_AbstractSeqIterObject.inst_index .*>)
            guard_not_invalidated(descr=...)
            i23 = int_lt(i18, 0)
            guard_false(i23, descr=...)
            i25 = int_ge(i18, i9)
            guard_false(i25, descr=...)
            i27 = int_add_ovf(i7, i18)
            guard_no_overflow(descr=...)
            --TICK--
            jump(..., descr=<Loop0>)
        """)


    def test_chain_of_guards(self):
        src = """
        class A(object):
            def method_x(self):
                return 3

        l = ["x", "y"]

        def main(arg):
            sum = 0
            a = A()
            i = 0
            while i < 500:
                name = l[arg]
                sum += getattr(a, 'method_' + name)()
                i += 1
            return sum
        """
        log = self.run(src, [0])
        assert log.result == 500*3
        loops = log.loops_by_filename(self.filepath)
        assert len(loops) == 1


    def test_unpack_iterable_non_list_tuple(self):
        def main(n):
            import array

            items = [array.array("i", [1])] * n
            total = 0
            for a, in items:
                total += a
            return total

        log = self.run(main, [1000000])
        assert log.result == 1000000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i16 = int_ge(i12, i13)
            guard_false(i16, descr=...)
            p17 = getarrayitem_gc(p15, i12, descr=<GcPtrArrayDescr>)
            i19 = int_add(i12, 1)
            setfield_gc(p9, i19, descr=<SignedFieldDescr .*W_AbstractSeqIterObject.inst_index .*>)
            guard_nonnull_class(p17, 146982464, descr=...)
            i21 = getfield_gc(p17, descr=<SignedFieldDescr .*W_ArrayTypei.inst_len .*>)
            i23 = int_lt(0, i21)
            guard_true(i23, descr=...)
            i24 = getfield_gc(p17, descr=<NonGcPtrFieldDescr .*W_ArrayTypei.inst_buffer .*>)
            i25 = getarrayitem_raw(i24, 0, descr=<.*>)
            i27 = int_lt(1, i21)
            guard_false(i27, descr=...)
            i28 = int_add_ovf(i10, i25)
            guard_no_overflow(descr=...)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, p6, i28, i25, p9, p10, p11, i19, i13, p14, p15, descr=<Loop0>)
        """)


    def test_dont_trace_every_iteration(self):
        def main(a, b):
            i = sa = 0
            while i < 300:
                if a > 0:
                    pass
                if 1 < b < 2:
                    pass
                sa += a % b
                i += 1
            return sa
        #
        log = self.run(main, [10, 20])
        assert log.result == 300 * (10 % 20)
        assert log.jit_summary.tracing_no == 1
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i11 = int_lt(i7, 300)
            guard_true(i11, descr=...)
            i12 = int_add_ovf(i8, i9)
            guard_no_overflow(descr=...)
            i14 = int_add(i7, 1)
            --TICK--
            jump(..., descr=...)
        """)
        #
        log = self.run(main, [-10, -20])
        assert log.result == 300 * (-10 % -20)
        assert log.jit_summary.tracing_no == 1


    def test_overflow_checking(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        def main():
            import sys
            def f(a,b):
                if a < 0: return -1
                return a-b
            #
            total = sys.maxint - 2147483647
            for i in range(100000):
                total += f(i, 5)
            #
            return total
        #
        self.run_and_check(main, [])


    def test_global(self):
        log = self.run("""
        i = 0
        globalinc = 1
        def main(n):
            global i
            while i < n:
                l = globalinc # ID: globalread
                i += l
        """, [1000])

        loop, = log.loops_by_id("globalread", is_entry_bridge=True)
        assert len(loop.ops_by_id("globalread")) == 0

    def test_struct_module(self):
        def main():
            import struct
            i = 1
            while i < 1000:
                x = struct.unpack("i", struct.pack("i", i))[0] # ID: struct
                i += x / i
            return i

        log = self.run(main)
        assert log.result == main()

        loop, = log.loops_by_id("struct")
        # This could, of course stand some improvement, to remove all these
        # arithmatic ops, but we've removed all the core overhead.
        if sys.maxint == 31 ** 2:
            extra = """
            i8 = int_lt(i4, -2147483648)
            guard_false(i8, descr=...)
            """
        else:
            extra = ""
        assert loop.match_by_id("struct", """
            guard_not_invalidated(descr=...)
            # struct.pack
            %(32_bit_only)s
            i11 = int_and(i4, 255)
            i13 = int_rshift(i4, 8)
            i14 = int_and(i13, 255)
            i16 = int_rshift(i13, 8)
            i17 = int_and(i16, 255)
            i19 = int_rshift(i16, 8)
            i20 = int_and(i19, 255)

            # struct.unpack
            i22 = int_lshift(i14, 8)
            i23 = int_or(i11, i22)
            i25 = int_lshift(i17, 16)
            i26 = int_or(i23, i25)
            i28 = int_ge(i20, 128)
            guard_false(i28, descr=...)
            i30 = int_lshift(i20, 24)
            i31 = int_or(i26, i30)
        """ % {"32_bit_only": extra})