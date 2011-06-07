import py, sys
from pypy.module.pypyjit.test_pypy_c.test_model import BaseTestPyPyC


class TestPyPyCNew(BaseTestPyPyC):
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
            p11 = call(ConstClass(rbigint.mul), p5, p9, descr=...)
            guard_no_exception(descr=...)
            i13 = int_sub(i4, 1)
            --TICK--
            jump(p0, p1, p2, p3, i13, p11, descr=...)
        """)



    def test_virtual_instance(self):
        def main(n):
            class A(object):
                pass
            #
            i = 0
            while i < n:
                a = A()
                assert isinstance(a, A)
                assert not isinstance(a, int)
                a.x = 2
                i = i + a.x
            return i
        #
        log = self.run(main, [1000], threshold = 400)
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i5, i6)
            guard_true(i7, descr=<Guard3>)
            guard_not_invalidated(descr=<Guard4>)
            i9 = int_add_ovf(i5, 2)
            guard_no_overflow(descr=<Guard5>)
            --TICK--
            jump(p0, p1, p2, p3, p4, i9, i6, descr=<Loop0>)
        """)

    def test_load_attr(self):
        src = '''
            class A(object):
                pass
            a = A()
            a.x = 2
            def main(n):
                i = 0
                while i < n:
                    i = i + a.x
                return i
        '''
        log = self.run(src, [1000])
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i9 = int_lt(i5, i6)
            guard_true(i9, descr=<Guard3>)
            guard_not_invalidated(descr=<Guard4>)
            i10 = int_add_ovf(i5, i7)
            guard_no_overflow(descr=<Guard5>)
            --TICK--
            jump(p0, p1, p2, p3, p4, i10, i6, p7, i7, p8, descr=<Loop0>)
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
            guard_true(i9, descr=<Guard3>)
            f10 = float_add(f8, f5)
            --TICK--
            jump(p0, p1, p2, p3, p4, f10, p6, f7, f8, descr=<Loop0>)
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
            guard_false(i16, descr=<Guard3>)
            i17 = int_mul(i11, i14)
            i18 = int_add(i15, i17)
            i20 = int_add(i11, 1)
            i21 = force_token()
            setfield_gc(p4, i20, descr=<.* .*W_AbstractSeqIterObject.inst_index .*>)
            guard_not_invalidated(descr=<Guard4>)
            i23 = int_lt(i18, 0)
            guard_false(i23, descr=<Guard5>)
            i25 = int_ge(i18, i9)
            guard_false(i25, descr=<Guard6>)
            i27 = int_add_ovf(i7, i18)
            guard_no_overflow(descr=<Guard7>)
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

    def test_getattr_with_dynamic_attribute(self):
        src = """
        class A(object):
            pass

        l = ["x", "y"]

        def main():
            sum = 0
            a = A()
            a.a1 = 0
            a.a2 = 0
            a.a3 = 0
            a.a4 = 0
            a.a5 = 0 # workaround, because the first five attributes need a promotion
            a.x = 1
            a.y = 2
            i = 0
            while i < 500:
                name = l[i % 2]
                sum += getattr(a, name)
                i += 1
            return sum
        """
        log = self.run(src, [])
        assert log.result == 250 + 250*2
        loops = log.loops_by_filename(self.filepath)
        assert len(loops) == 1


    def test_import_in_function(self):
        def main(n):
            i = 0
            while i < n:
                from sys import version  # ID: import
                i += 1
            return i
        #
        log = self.run(main, [500])
        assert log.result == 500
        loop, = log.loops_by_id('import')
        assert loop.match_by_id('import', """
            p11 = getfield_gc(ConstPtr(ptr10), descr=<GcPtrFieldDescr pypy.objspace.std.celldict.ModuleCell.inst_w_value 8>)
            guard_value(p11, ConstPtr(ptr12), descr=<Guard4>)
            guard_not_invalidated(descr=<Guard5>)
            p14 = getfield_gc(ConstPtr(ptr13), descr=<GcPtrFieldDescr pypy.objspace.std.celldict.ModuleCell.inst_w_value 8>)
            p16 = getfield_gc(ConstPtr(ptr15), descr=<GcPtrFieldDescr pypy.objspace.std.celldict.ModuleCell.inst_w_value 8>)
            guard_value(p14, ConstPtr(ptr17), descr=<Guard6>)
            guard_isnull(p16, descr=<Guard7>)
        """)

    def test_import_fast_path(self, tmpdir):
        pkg = tmpdir.join('mypkg').ensure(dir=True)
        pkg.join('__init__.py').write("")
        pkg.join('mod.py').write(str(py.code.Source("""
            def do_the_import():
                import sys
        """)))
        def main(path, n):
            import sys
            sys.path.append(path)
            from mypkg.mod import do_the_import
            for i in range(n):
                do_the_import()
        #
        log = self.run(main, [str(tmpdir), 300])
        loop, = log.loops_by_filename(self.filepath)
        # this is a check for a slow-down that introduced a
        # call_may_force(absolute_import_with_lock).
        for opname in log.opnames(loop.allops(opcode="IMPORT_NAME")):
            assert 'call' not in opname    # no call-like opcode


    def test__ffi_call_releases_gil(self):
        from pypy.rlib.test.test_libffi import get_libc_name
        def main(libc_name, n):
            import time
            from threading import Thread
            from _ffi import CDLL, types
            #
            libc = CDLL(libc_name)
            sleep = libc.getfunc('sleep', [types.uint], types.uint)
            delays = [0]*n + [1]
            #
            def loop_of_sleeps(i, delays):
                for delay in delays:
                    sleep(delay)    # ID: sleep
            #
            threads = [Thread(target=loop_of_sleeps, args=[i, delays]) for i in range(5)]
            start = time.time()
            for i, thread in enumerate(threads):
                thread.start()
            for thread in threads:
                thread.join()
            end = time.time()
            return end - start
        #
        log = self.run(main, [get_libc_name(), 200], threshold=150)
        assert 1 <= log.result <= 1.5 # at most 0.5 seconds of overhead
        loops = log.loops_by_id('sleep')
        assert len(loops) == 1 # make sure that we actually JITted the loop

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
            guard_false(i16, descr=<Guard3>)
            p17 = getarrayitem_gc(p15, i12, descr=<GcPtrArrayDescr>)
            i19 = int_add(i12, 1)
            setfield_gc(p4, i19, descr=<SignedFieldDescr .*W_AbstractSeqIterObject.inst_index .*>)
            guard_nonnull_class(p17, 146982464, descr=<Guard4>)
            i21 = getfield_gc(p17, descr=<SignedFieldDescr .*W_ArrayTypei.inst_len .*>)
            i23 = int_lt(0, i21)
            guard_true(i23, descr=<Guard5>)
            i24 = getfield_gc(p17, descr=<NonGcPtrFieldDescr .*W_ArrayTypei.inst_buffer .*>)
            i25 = getarrayitem_raw(i24, 0, descr=<.*>)
            i27 = int_lt(1, i21)
            guard_false(i27, descr=<Guard6>)
            i28 = int_add_ovf(i10, i25)
            guard_no_overflow(descr=<Guard7>)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, i28, i25, i19, i13, p14, p15, descr=<Loop0>)
        """)

    def test_mutate_class(self):
        def fn(n):
            class A(object):
                count = 1
                def __init__(self, a):
                    self.a = a
                def f(self):
                    return self.count
            i = 0
            a = A(1)
            while i < n:
                A.count += 1 # ID: mutate
                i = a.f()    # ID: meth1
            return i
        #
        log = self.run(fn, [1000], threshold=10)
        assert log.result == 1000
        #
        # first, we test the entry bridge
        # -------------------------------
        entry_bridge, = log.loops_by_filename(self.filepath, is_entry_bridge=True)
        ops = entry_bridge.ops_by_id('mutate', opcode='LOAD_ATTR')
        assert log.opnames(ops) == ['guard_value', 'guard_not_invalidated',
                                    'getfield_gc', 'guard_nonnull_class']
        # the STORE_ATTR is folded away
        assert list(entry_bridge.ops_by_id('meth1', opcode='STORE_ATTR')) == []
        #
        # then, the actual loop
        # ----------------------
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i8 = getfield_gc_pure(p5, descr=<SignedFieldDescr .*W_IntObject.inst_intval.*>)
            i9 = int_lt(i8, i7)
            guard_true(i9, descr=.*)
            guard_not_invalidated(descr=.*)
            i11 = int_add(i8, 1)
            i12 = force_token()
            --TICK--
            p20 = new_with_vtable(ConstClass(W_IntObject))
            setfield_gc(p20, i11, descr=<SignedFieldDescr.*W_IntObject.inst_intval .*>)
            setfield_gc(ConstPtr(ptr21), p20, descr=<GcPtrFieldDescr .*TypeCell.inst_w_value .*>)
            jump(p0, p1, p2, p3, p4, p20, p6, i7, descr=<Loop.>)
        """)



    def test_min_max(self):
        def main():
            i=0
            sa=0
            while i < 300:
                sa+=min(max(i, 3000), 4000)
                i+=1
            return sa
        log = self.run(main, [])
        assert log.result == 300*3000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i4, 300)
            guard_true(i7, descr=...)
            i9 = int_add_ovf(i5, 3000)
            guard_no_overflow(descr=...)
            i11 = int_add(i4, 1)
            --TICK--
            jump(p0, p1, p2, p3, i11, i9, descr=<Loop0>)
        """)

    def test_silly_max(self):
        def main():
            i = 2
            sa = 0
            while i < 300:
                lst = range(i)
                sa += max(*lst) # ID: max
                i += 1
            return sa
        log = self.run(main, [])
        assert log.result == main()
        loop, = log.loops_by_filename(self.filepath)
        # We dont want too many guards, but a residual call to min_max_loop
        guards = [n for n in log.opnames(loop.ops_by_id("max")) if n.startswith('guard')]
        assert len(guards) < 20
        assert loop.match_by_id('max',"""
            ...
            p76 = call_may_force(ConstClass(min_max_loop__max), _, _, descr=...)
            ...
        """)

    def test_iter_max(self):
        def main():
            i = 2
            sa = 0
            while i < 300:
                lst = range(i)
                sa += max(lst) # ID: max
                i += 1
            return sa
        log = self.run(main, [])
        assert log.result == main()
        loop, = log.loops_by_filename(self.filepath)
        # We dont want too many guards, but a residual call to min_max_loop
        guards = [n for n in log.opnames(loop.ops_by_id("max")) if n.startswith('guard')]
        assert len(guards) < 20
        assert loop.match_by_id('max',"""
            ...
            p76 = call_may_force(ConstClass(min_max_loop__max), _, _, descr=...)
            ...
        """)

    def test__ffi_call(self):
        from pypy.rlib.test.test_libffi import get_libm_name
        def main(libm_name):
            try:
                from _ffi import CDLL, types
            except ImportError:
                sys.stderr.write('SKIP: cannot import _ffi\n')
                return 0

            libm = CDLL(libm_name)
            pow = libm.getfunc('pow', [types.double, types.double],
                               types.double)
            i = 0
            res = 0
            while i < 300:
                tmp = pow(2, 3)   # ID: fficall
                res += tmp
                i += 1
            return pow.getaddr(), res
        #
        libm_name = get_libm_name(sys.platform)
        log = self.run(main, [libm_name])
        pow_addr, res = log.result
        assert res == 8.0 * 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('fficall', """
            p16 = getfield_gc(ConstPtr(ptr15), descr=<.* .*Function.inst_name .*>)
            guard_not_invalidated(descr=...)
            i17 = force_token()
            setfield_gc(p0, i17, descr=<.* .*PyFrame.vable_token .*>)
            f21 = call_release_gil(%d, 2.000000, 3.000000, descr=<FloatCallDescr>)
            guard_not_forced(descr=...)
            guard_no_exception(descr=...)
        """ % pow_addr)


    def test__ffi_call_frame_does_not_escape(self):
        from pypy.rlib.test.test_libffi import get_libm_name
        def main(libm_name):
            try:
                from _ffi import CDLL, types
            except ImportError:
                sys.stderr.write('SKIP: cannot import _ffi\n')
                return 0

            libm = CDLL(libm_name)
            pow = libm.getfunc('pow', [types.double, types.double],
                               types.double)

            def mypow(a, b):
                return pow(a, b)

            i = 0
            res = 0
            while i < 300:
                tmp = mypow(2, 3)
                res += tmp
                i += 1
            return pow.getaddr(), res
        #
        libm_name = get_libm_name(sys.platform)
        log = self.run(main, [libm_name])
        pow_addr, res = log.result
        assert res == 8.0 * 300
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        # we only force the virtualref, not its content
        assert opnames.count('new_with_vtable') == 1

    def test_ctypes_call(self):
        from pypy.rlib.test.test_libffi import get_libm_name
        def main(libm_name):
            import ctypes
            libm = ctypes.CDLL(libm_name)
            fabs = libm.fabs
            fabs.argtypes = [ctypes.c_double]
            fabs.restype = ctypes.c_double
            x = -4
            i = 0
            while i < 300:
                x = fabs(x)
                x = x - 100
                i += 1
            return fabs._ptr.getaddr(), x

        libm_name = get_libm_name(sys.platform)
        log = self.run(main, [libm_name])
        fabs_addr, res = log.result
        assert res == -4.0
        loop, = log.loops_by_filename(self.filepath)
        ops = loop.allops()
        opnames = log.opnames(ops)
        assert opnames.count('new_with_vtable') == 1 # only the virtualref
        assert opnames.count('call_release_gil') == 1
        idx = opnames.index('call_release_gil')
        call = ops[idx]
        assert int(call.args[0]) == fabs_addr

    def test_xor(self):
        def main(b):
            a = sa = 0
            while a < 300:
                if a > 0: # Specialises the loop
                    pass
                if b > 10:
                    pass
                if a^b >= 0:  # ID: guard
                    sa += 1
                sa += a^a     # ID: a_xor_a
                a += 1
            return sa

        log = self.run(main, [11])
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        # if both are >=0, a^b is known to be >=0
        # note that we know that b>10
        assert loop.match_by_id('guard', """
            i10 = int_xor(i5, i7)
        """)
        #
        # x^x is always optimized to 0
        assert loop.match_by_id('a_xor_a', "")

        log = self.run(main, [9])
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        # we don't know that b>10, hence we cannot optimize it
        assert loop.match_by_id('guard', """
            i10 = int_xor(i5, i7)
            i12 = int_ge(i10, 0)
            guard_true(i12, descr=...)
        """)


    def test_oldstyle_newstyle_mix(self):
        def main():
            class A:
                pass

            class B(object, A):
                def __init__(self, x):
                    self.x = x

            i = 0
            b = B(1)
            while i < 100:
                v = b.x # ID: loadattr
                i += v
            return i

        log = self.run(main, [], threshold=80)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('loadattr',
        '''
        guard_not_invalidated(descr=...)
        i19 = call(ConstClass(ll_dict_lookup), _, _, _, descr=...)
        guard_no_exception(descr=...)
        i21 = int_and(i19, _)
        i22 = int_is_true(i21)
        guard_true(i22, descr=...)
        i26 = call(ConstClass(ll_dict_lookup), _, _, _, descr=...)
        guard_no_exception(descr=...)
        i28 = int_and(i26, _)
        i29 = int_is_true(i28)
        guard_true(i29, descr=...)
        ''')

    def test_python_contains(self):
        def main():
            class A(object):
                def __contains__(self, v):
                    return True

            i = 0
            a = A()
            while i < 100:
                i += i in a # ID: contains
                b = 0       # to make sure that JUMP_ABSOLUTE is not part of the ID

        log = self.run(main, [], threshold=80)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id("contains", """
            guard_not_invalidated(descr=...)
            i11 = force_token()
            i12 = int_add_ovf(i5, i7)
            guard_no_overflow(descr=...)
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
            guard_true(i11, descr=<Guard3>)
            i12 = int_add_ovf(i8, i9)
            guard_no_overflow(descr=<Guard4>)
            i14 = int_add(i7, 1)
            --TICK--
            jump(..., descr=...)
        """)
        #
        log = self.run(main, [-10, -20])
        assert log.result == 300 * (-10 % -20)
        assert log.jit_summary.tracing_no == 1

    def test_id_compare_optimization(self):
        def main():
            class A(object):
                pass
            #
            i = 0
            a = A()
            while i < 300:
                new_a = A()
                if new_a != a:  # ID: compare
                    pass
                i += 1
            return i
        #
        log = self.run(main, [])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id("compare", "") # optimized away

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
