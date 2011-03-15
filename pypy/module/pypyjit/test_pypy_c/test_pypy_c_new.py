import py, sys, re
import subprocess
from lib_pypy import disassembler
from pypy.tool.udir import udir
from pypy.tool import logparser
from pypy.module.pypyjit.test_pypy_c.model import Log
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
            guard_no_exception(descr=...)
            p11 = call(ConstClass(rbigint.mul), p5, p9, descr=...)
            guard_no_exception(descr=...)
            i13 = int_sub(i4, 1)
            --TICK--
            jump(p0, p1, p2, p3, i13, p11, descr=...)
        """)


    def test_recursive_call(self):
        def fn():
            def rec(n):
                if n == 0:
                    return 0
                return 1 + rec(n-1)
            #
            # this loop is traced and then aborted, because the trace is too
            # long. But then "rec" is marked as "don't inline"
            i = 0
            j = 0
            while i < 20:
                i += 1
                j += rec(100)
            #
            # next time we try to trace "rec", instead of inlining we compile
            # it separately and generate a call_assembler
            i = 0
            j = 0
            while i < 20:
                i += 1
                j += rec(100) # ID: call_rec
                a = 0
            return j
        #
        log = self.run(fn, [], threshold=18)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('call_rec', """
            ...
            p53 = call_assembler(p35, p7, ConstPtr(ptr21), ConstPtr(ptr49), 0, ConstPtr(ptr51), -1, ConstPtr(ptr52), ConstPtr(ptr52), ConstPtr(ptr52), ConstPtr(ptr52), ConstPtr(ptr48), descr=...)
            guard_not_forced(descr=...)
            guard_no_exception(descr=...)
            ...
        """)

    def test_cmp_exc(self):
        def f1(n):
            # So we don't get a LOAD_GLOBAL op
            KE = KeyError
            i = 0
            while i < n:
                try:
                    raise KE
                except KE: # ID: except
                    i += 1
            return i

        log = self.run(f1, [10000])
        assert log.result == 10000
        loop, = log.loops_by_id("except")
        ops = list(loop.ops_by_id("except", opcode="COMPARE_OP"))
        assert ops == []

    def test_simple_call(self):
        src = """
            OFFSET = 0
            def f(i):
                return i + 1 + OFFSET # ID: add
            def main(n):
                i = 0
                while i < n+OFFSET:   # ID: cond
                    i = f(f(i))       # ID: call
                    a = 0
                return i
        """
        log = self.run(src, [1000], threshold=400)
        assert log.result == 1000
        # first, we test what is inside the entry bridge
        # -----------------------------------------------
        entry_bridge, = log.loops_by_id('call', is_entry_bridge=True)
        # LOAD_GLOBAL of OFFSET
        ops = entry_bridge.ops_by_id('cond', opcode='LOAD_GLOBAL')
        assert log.opnames(ops) == ["guard_value",
                                    "getfield_gc", "guard_value",
                                    "getfield_gc", "guard_isnull",
                                    "getfield_gc", "guard_nonnull_class"]
        # LOAD_GLOBAL of OFFSET but in different function partially folded
        # away
        # XXX could be improved
        ops = entry_bridge.ops_by_id('add', opcode='LOAD_GLOBAL')
        assert log.opnames(ops) == ["guard_value", "getfield_gc", "guard_isnull"]
        #
        # two LOAD_GLOBAL of f, the second is folded away
        ops = entry_bridge.ops_by_id('call', opcode='LOAD_GLOBAL')
        assert log.opnames(ops) == ["getfield_gc", "guard_nonnull_class"]
        #
        assert entry_bridge.match_by_id('call', """
            p29 = getfield_gc(ConstPtr(ptr28), descr=<GcPtrFieldDescr pypy.objspace.std.celldict.ModuleCell.inst_w_value .*>)
            guard_nonnull_class(p29, ConstClass(Function), descr=<Guard17>)
            i32 = getfield_gc(p0, descr=<BoolFieldDescr pypy.interpreter.pyframe.PyFrame.inst_is_being_profiled .*>)
            guard_false(i32, descr=<Guard18>)
            p33 = getfield_gc(p29, descr=<GcPtrFieldDescr pypy.interpreter.function.Function.inst_code .*>)
            guard_value(p33, ConstPtr(ptr34), descr=<Guard19>)
            p35 = getfield_gc(p29, descr=<GcPtrFieldDescr pypy.interpreter.function.Function.inst_w_func_globals .*>)
            p36 = getfield_gc(p29, descr=<GcPtrFieldDescr pypy.interpreter.function.Function.inst_closure .*>)
            p38 = call(ConstClass(getexecutioncontext), descr=<GcPtrCallDescr>)
            p39 = getfield_gc(p38, descr=<GcPtrFieldDescr pypy.interpreter.executioncontext.ExecutionContext.inst_topframeref .*>)
            i40 = force_token()
            p41 = getfield_gc(p38, descr=<GcPtrFieldDescr pypy.interpreter.executioncontext.ExecutionContext.inst_w_tracefunc .*>)
            guard_isnull(p41, descr=<Guard20>)
            i42 = getfield_gc(p38, descr=<NonGcPtrFieldDescr pypy.interpreter.executioncontext.ExecutionContext.inst_profilefunc .*>)
            i43 = int_is_zero(i42)
            guard_true(i43, descr=<Guard21>)
            i50 = force_token()
        """)
        #
        # then, we test the actual loop
        # -----------------------------
        loop, = log.loops_by_id('call')
        assert loop.match("""
            i12 = int_lt(i5, i6)
            guard_true(i12, descr=<Guard3>)
            i13 = force_token()
            i15 = int_add(i5, 1)
            i16 = int_add_ovf(i15, i7)
            guard_no_overflow(descr=<Guard4>)
            i18 = force_token()
            i20 = int_add_ovf(i16, 1)
            guard_no_overflow(descr=<Guard5>)
            i21 = int_add_ovf(i20, i7)
            guard_no_overflow(descr=<Guard6>)
            --TICK--
            jump(p0, p1, p2, p3, p4, i21, i6, i7, p8, p9, p10, p11, descr=<Loop0>)
        """)

    def test_method_call(self):
        def fn(n):
            class A(object):
                def __init__(self, a):
                    self.a = a
                def f(self, i):
                    return self.a + i
            i = 0
            a = A(1)
            while i < n:
                x = a.f(i)    # ID: meth1
                i = a.f(x)    # ID: meth2
            return i
        #
        log = self.run(fn, [1000], threshold=400)
        assert log.result == 1000
        #
        # first, we test the entry bridge
        # -------------------------------
        entry_bridge, = log.loops_by_filename(self.filepath, is_entry_bridge=True)
        ops = entry_bridge.ops_by_id('meth1', opcode='LOOKUP_METHOD')
        assert log.opnames(ops) == ['guard_value', 'getfield_gc', 'guard_value',
                                    'getfield_gc', 'guard_value']
        # the second LOOKUP_METHOD is folded away
        assert list(entry_bridge.ops_by_id('meth2', opcode='LOOKUP_METHOD')) == []
        #
        # then, the actual loop
        # ----------------------
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i15 = int_lt(i6, i9)
            guard_true(i15, descr=<Guard3>)
            i16 = force_token()
            i17 = int_add_ovf(i10, i6)
            guard_no_overflow(descr=<Guard4>)
            i18 = force_token()
            i19 = int_add_ovf(i10, i17)
            guard_no_overflow(descr=<Guard5>)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i19, p7, i17, i9, i10, p11, p12, p13, p14, descr=<Loop0>)
        """)

    def test_static_classmethod_call(self):
        def fn(n):
            class A(object):
                @classmethod
                def f(cls, i):
                    return i + (cls is A) + 1
                @staticmethod
                def g(i):
                    return i - 1
            #
            i = 0
            a = A()
            while i < n:
                x = a.f(i)
                i = a.g(x)
            return i
        #
        log = self.run(fn, [1000], threshold=400)
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i14 = int_lt(i6, i9)
            guard_true(i14, descr=<Guard3>)
            i15 = force_token()
            i17 = int_add_ovf(i8, 1)
            guard_no_overflow(descr=<Guard4>)
            i18 = force_token()
            i20 = int_sub(i17, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i20, p7, i17, i9, p10, p11, p12, p13, descr=<Loop0>)
        """)

    def test_default_and_kw(self):
        def main(n):
            def f(i, j=1):
                return i + j
            #
            i = 0
            while i < n:
                i = f(f(i), j=1) # ID: call
                a = 0
            return i
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 1000
        loop, = log.loops_by_id('call')
        assert loop.match_by_id('call', """
            i14 = force_token()
            i16 = force_token()
        """)

    def test_kwargs(self):
        # this is not a very precise test, could be improved
        def main(x):
            def g(**args):
                return len(args)
            #
            s = 0
            d = {}
            for i in range(x):
                s += g(**d)       # ID: call
                d[str(i)] = i
                if i % 100 == 99:
                    d = {}
            return s
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 49500
        loop, = log.loops_by_id('call')
        ops = log.opnames(loop.ops_by_id('call'))
        guards = [ops for ops in ops if ops.startswith('guard')]
        assert len(guards) <= 5

    def test_stararg_virtual(self):
        def main(x):
            def g(*args):
                return len(args)
            def h(a, b, c):
                return c
            #
            s = 0
            for i in range(x):
                l = [i, x, 2]
                s += g(*l)       # ID: g1
                s += h(*l)       # ID: h1
                s += g(i, x, 2)  # ID: g2
                a = 0
            for i in range(x):
                l = [x, 2]
                s += g(i, *l)    # ID: g3
                s += h(i, *l)    # ID: h2
                a = 0
            return s
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 13000
        loop0, = log.loops_by_id('g1')
        assert loop0.match_by_id('g1', """
            i20 = force_token()
            setfield_gc(p4, i19, descr=<.*W_AbstractSeqIterObject.inst_index .*>)
            i22 = int_add_ovf(i8, 3)
            guard_no_overflow(descr=<Guard4>)
        """)
        assert loop0.match_by_id('h1', """
            i20 = force_token()
            i22 = int_add_ovf(i8, 2)
            guard_no_overflow(descr=<Guard5>)
        """)
        assert loop0.match_by_id('g2', """
            i27 = force_token()
            i29 = int_add_ovf(i26, 3)
            guard_no_overflow(descr=<Guard6>)
        """)
        #
        loop1, = log.loops_by_id('g3')
        assert loop1.match_by_id('g3', """
            i21 = force_token()
            setfield_gc(p4, i20, descr=<.* .*W_AbstractSeqIterObject.inst_index .*>)
            i23 = int_add_ovf(i9, 3)
            guard_no_overflow(descr=<Guard37>)
        """)
        assert loop1.match_by_id('h2', """
            i25 = force_token()
            i27 = int_add_ovf(i23, 2)
            guard_no_overflow(descr=<Guard38>)
        """)

    def test_stararg(self):
        def main(x):
            def g(*args):
                return args[-1]
            def h(*args):
                return len(args)
            #
            s = 0
            l = []
            i = 0
            while i < x:
                l.append(1)
                s += g(*l)     # ID: g
                i = h(*l)      # ID: h
                a = 0
            return s
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 1000
        loop, = log.loops_by_id('g')
        ops_g = log.opnames(loop.ops_by_id('g'))
        ops_h = log.opnames(loop.ops_by_id('h'))
        ops = ops_g + ops_h
        assert 'new_with_vtable' not in ops
        assert 'call_may_force' not in ops

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
            i9 = int_add_ovf(i5, 2)
            guard_no_overflow(descr=<Guard4>)
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
        log = self.run(src, [1000], threshold=400)
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i9 = int_lt(i5, i6)
            guard_true(i9, descr=<Guard3>)
            i10 = int_add_ovf(i5, i7)
            guard_no_overflow(descr=<Guard4>)
            --TICK--
            jump(p0, p1, p2, p3, p4, i10, i6, i7, p8, descr=<Loop0>)
        """)

    def test_mixed_type_loop(self):
        def main(n):
            i = 0.0
            j = 2
            while i < n:
                i = j + i
            return i
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 1000.0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i9 = float_lt(f5, f7)
            guard_true(i9, descr=<Guard3>)
            f10 = float_add(f8, f5)
            --TICK--
            jump(p0, p1, p2, p3, p4, f10, p6, f7, f8, descr=<Loop0>)
        """)

    def test_call_builtin_function(self):
        def main(n):
            i = 2
            l = []
            while i < n:
                i += 1
                l.append(i)    # ID: append
                a = 0
            return i, len(l)
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == (1000, 998)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('append', """
            p14 = new_with_vtable(ConstClass(W_IntObject))
            setfield_gc(p14, i12, descr=<SignedFieldDescr .*W_IntObject.inst_intval .*>)
            call(ConstClass(ll_append__listPtr_objectPtr), p8, p14, descr=...)
            guard_no_exception(descr=<Guard4>)
        """)

    def test_range_iter(self):
        def main(n):
            def g(n):
                return range(n)
            s = 0
            for i in range(n):  # ID: for
                tmp = g(n)
                s += tmp[i]     # ID: getitem
            return s
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 1000 * 999 / 2
        loop, = log.loops_by_filename(self.filepath)
        loop.match_by_id('getitem', opcode='BINARY_SUBSCR', expected_src="""
            i43 = int_lt(i25, 0)
            guard_false(i43, descr=<Guard9>)
            i44 = int_ge(i25, i39)
            guard_false(i44, descr=<Guard10>)
            i45 = int_mul(i25, i33)
        """)
        loop.match_by_id('for', opcode='FOR_ITER', expected_src="""
            i23 = int_ge(i11, i12)
            guard_false(i23, descr=<Guard3>)
            i24 = int_mul(i11, i14)
            i25 = int_add(i15, i24)
            i27 = int_add(i11, 1)
            # even if it's a the end of the loop, the jump still belongs to
            # the FOR_ITER opcode
            jump(p0, p1, p2, p3, p4, p5, p6, i46, i25, i39, i33, i27, i12, p13, i14, i15, p16, i17, i18, p19, p20, i21, i22, descr=<Loop0>)
        """)


    def test_exception_inside_loop_1(self):
        def main(n):
            while n:
                try:
                    raise ValueError
                except ValueError:
                    pass
                n -= 1
            return n
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
        i5 = int_is_true(i3)
        guard_true(i5, descr=<Guard3>)
        --EXC-TICK--
        i12 = int_sub_ovf(i3, 1)
        guard_no_overflow(descr=<Guard5>)
        --TICK--
        jump(p0, p1, p2, i12, p4, descr=<Loop0>)
        """)

    def test_reraise(self):
        def f(n):
            i = 0
            while i < n:
                try:
                    try:
                        raise KeyError
                    except KeyError:
                        raise
                except KeyError:
                    i += 1
            return i

        log = self.run(f, [100000])
        assert log.result == 100000
        loop, = log.loops_by_filename(self.filepath)
