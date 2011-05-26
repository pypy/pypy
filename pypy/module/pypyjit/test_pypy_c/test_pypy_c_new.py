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
            p53 = call_assembler(..., descr=...)
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
            guard_nonnull_class(p29, ConstClass(Function), descr=<Guard18>)
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
                                    'guard_not_invalidated']
        # the second LOOKUP_METHOD is folded away
        assert list(entry_bridge.ops_by_id('meth2', opcode='LOOKUP_METHOD')) == []
        #
        # then, the actual loop
        # ----------------------
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i15 = int_lt(i6, i9)
            guard_true(i15, descr=<Guard3>)
            guard_not_invalidated(descr=<Guard4>)
            i16 = force_token()
            i17 = int_add_ovf(i10, i6)
            guard_no_overflow(descr=<Guard5>)
            i18 = force_token()
            i19 = int_add_ovf(i10, i17)
            guard_no_overflow(descr=<Guard6>)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i19, p7, i17, i9, i10, p11, p12, p13, descr=<Loop0>)
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
            guard_not_invalidated(descr=<Guard4>)
            i15 = force_token()
            i17 = int_add_ovf(i8, 1)
            guard_no_overflow(descr=<Guard5>)
            i18 = force_token()
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i8, p7, i17, i9, p10, p11, p12, descr=<Loop0>)
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
        log = self.run(src, [1000], threshold=400)
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
                a = 0
            return s
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 1000 * 999 / 2
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i11 = getfield_gc(p4, descr=<.* .*W_AbstractSeqIterObject.inst_index .*>)
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
        guard_not_invalidated(descr=<Guard4>)
        --EXC-TICK--
        i12 = int_sub_ovf(i3, 1)
        guard_no_overflow(descr=<Guard6>)
        --TICK--
        jump(..., descr=<Loop0>)
        """)

    def test_exception_inside_loop_2(self):
        def main(n):
            def g(n):
                raise ValueError(n)  # ID: raise
            def f(n):
                g(n)
            #
            while n:
                try:
                    f(n)
                except ValueError:
                    pass
                n -= 1
            return n
        #
        log = self.run(main, [1000], threshold=400)
        assert log.result == 0
        loop, = log.loops_by_filename(self.filepath)
        ops = log.opnames(loop.ops_by_id('raise'))
        assert 'new' not in ops

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
        assert loop.match("""
            i7 = int_lt(i4, i5)
            guard_true(i7, descr=<Guard3>)
            guard_not_invalidated(descr=<Guard4>)
            --EXC-TICK--
            i14 = int_add(i4, 1)
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
        log = self.run(src, [0], threshold=400)
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
        log = self.run(src, [], threshold=400)
        assert log.result == 250 + 250*2
        loops = log.loops_by_filename(self.filepath)
        assert len(loops) == 1

    def test_blockstack_virtualizable(self):
        def main(n):
            from pypyjit import residual_call
            i = 0
            while i < n:
                try:
                    residual_call(len, [])   # ID: call
                except:
                    pass
                i += 1
            return i
        #
        log = self.run(main, [500], threshold=400)
        assert log.result == 500
        loop, = log.loops_by_id('call')
        assert loop.match_by_id('call', opcode='CALL_FUNCTION', expected_src="""
            # make sure that the "block" is not allocated
            ...
            i20 = force_token()
            setfield_gc(p0, i20, descr=<SignedFieldDescr .*PyFrame.vable_token .*>)
            p22 = new_with_vtable(19511408)
            p24 = new_array(1, descr=<GcPtrArrayDescr>)
            p26 = new_with_vtable(ConstClass(W_ListObject))
            p27 = new(descr=<SizeDescr .*>)
            p29 = new_array(0, descr=<GcPtrArrayDescr>)
            setfield_gc(p27, p29, descr=<GcPtrFieldDescr list.items .*>)
            setfield_gc(p26, p27, descr=<.* .*W_ListObject.inst_wrappeditems .*>)
            setarrayitem_gc(p24, 0, p26, descr=<GcPtrArrayDescr>)
            setfield_gc(p22, p24, descr=<GcPtrFieldDescr .*Arguments.inst_arguments_w .*>)
            p32 = call_may_force(11376960, p18, p22, descr=<GcPtrCallDescr>)
            ...
        """)

    def test_import_in_function(self):
        def main(n):
            i = 0
            while i < n:
                from sys import version  # ID: import
                i += 1
            return i
        #
        log = self.run(main, [500], threshold=400)
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
        log = self.run(main, [str(tmpdir), 300], threshold=200)
        loop, = log.loops_by_filename(self.filepath)
        # this is a check for a slow-down that introduced a
        # call_may_force(absolute_import_with_lock).
        for opname in log.opnames(loop.allops(opcode="IMPORT_NAME")):
            assert 'call' not in opname    # no call-like opcode

    def test_arraycopy_disappears(self):
        def main(n):
            i = 0
            while i < n:
                t = (1, 2, 3, i + 1)
                t2 = t[:]
                del t
                i = t2[3]
                del t2
            return i
        #
        log = self.run(main, [500], threshold=400)
        assert log.result == 500
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i5, i6)
            guard_true(i7, descr=<Guard3>)
            i9 = int_add(i5, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, i9, i6, descr=<Loop0>)
        """)

    def test_boolrewrite_inverse(self):
        """
        Test for this case::
            guard(i < x)
            ...
            guard(i >= y)

        where x and y can be either constants or variables. There are cases in
        which the second guard is proven to be always true.
        """

        for a, b, res, opt_expected in (('2000', '2000', 20001000, True),
                                        ( '500',  '500', 15001500, True),
                                        ( '300',  '600', 16001700, False),
                                        (   'a',    'b', 16001700, False),
                                        (   'a',    'a', 13001700, True)):
            src = """
                def main():
                    sa = 0
                    a = 300
                    b = 600
                    for i in range(1000):
                        if i < %s:         # ID: lt
                            sa += 1
                        else:
                            sa += 2
                        #
                        if i >= %s:        # ID: ge
                            sa += 10000
                        else:
                            sa += 20000
                    return sa
            """ % (a, b)
            #
            log = self.run(src, [], threshold=400)
            assert log.result == res
            for loop in log.loops_by_filename(self.filepath):
                le_ops = log.opnames(loop.ops_by_id('lt'))
                ge_ops = log.opnames(loop.ops_by_id('ge'))
                assert le_ops.count('int_lt') == 1
                #
                if opt_expected:
                    assert ge_ops.count('int_ge') == 0
                else:
                    # if this assert fails it means that the optimization was
                    # applied even if we don't expect to. Check whether the
                    # optimization is valid, and either fix the code or fix the
                    # test :-)
                    assert ge_ops.count('int_ge') == 1

    def test_boolrewrite_reflex(self):
        """
        Test for this case::
            guard(i < x)
            ...
            guard(y > i)

        where x and y can be either constants or variables. There are cases in
        which the second guard is proven to be always true.
        """
        for a, b, res, opt_expected in (('2000', '2000', 10001000, True),
                                        ( '500',  '500', 15001500, True),
                                        ( '300',  '600', 14001700, False),
                                        (   'a',    'b', 14001700, False),
                                        (   'a',    'a', 17001700, True)):

            src = """
                def main():
                    sa = 0
                    a = 300
                    b = 600
                    for i in range(1000):
                        if i < %s:        # ID: lt
                            sa += 1
                        else:
                            sa += 2
                        if %s > i:        # ID: gt
                            sa += 10000
                        else:
                            sa += 20000
                    return sa
            """ % (a, b)
            log = self.run(src, [], threshold=400)
            assert log.result == res
            for loop in log.loops_by_filename(self.filepath):
                le_ops = log.opnames(loop.ops_by_id('lt'))
                gt_ops = log.opnames(loop.ops_by_id('gt'))
                assert le_ops.count('int_lt') == 1
                #
                if opt_expected:
                    assert gt_ops.count('int_gt') == 0
                else:
                    # if this assert fails it means that the optimization was
                    # applied even if we don't expect to. Check whether the
                    # optimization is valid, and either fix the code or fix the
                    # test :-)
                    assert gt_ops.count('int_gt') == 1


    def test_boolrewrite_allcases_inverse(self):
        """
        Test for this case::
            guard(i < x)
            ...
            guard(i > y)

        with all possible combination of binary comparison operators.  This
        test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        ops = ('<', '>', '<=', '>=', '==', '!=')
        for op1 in ops:
            for op2 in ops:
                for a,b in ((500, 500), (300, 600)):
                    src = """
                        def main():
                            sa = 0
                            for i in range(300):
                                if i %s %d:
                                    sa += 1
                                else:
                                    sa += 2
                                if i %s %d:
                                    sa += 10000
                                else:
                                    sa += 20000
                            return sa
                    """ % (op1, a, op2, b)
                    self.run_and_check(src, threshold=200)

                    src = """
                        def main():
                            sa = 0
                            i = 0.0
                            while i < 250.0:
                                if i %s %f:
                                    sa += 1
                                else:
                                    sa += 2
                                if i %s %f:
                                    sa += 10000
                                else:
                                    sa += 20000
                                i += 0.25
                            return sa
                    """ % (op1, float(a)/4.0, op2, float(b)/4.0)
                    self.run_and_check(src, threshold=300)


    def test_boolrewrite_allcases_reflex(self):
        """
        Test for this case::
            guard(i < x)
            ...
            guard(x > i)

        with all possible combination of binary comparison operators.  This
        test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        ops = ('<', '>', '<=', '>=', '==', '!=')
        for op1 in ops:
            for op2 in ops:
                for a,b in ((500, 500), (300, 600)):
                    src = """
                        def main():
                            sa = 0
                            for i in range(300):
                                if i %s %d:
                                    sa += 1
                                else:
                                    sa += 2
                                if %d %s i:
                                    sa += 10000
                                else:
                                    sa += 20000
                            return sa
                    """ % (op1, a, b, op2)
                    self.run_and_check(src, threshold=200)

                    src = """
                        def main():
                            sa = 0
                            i = 0.0
                            while i < 250.0:
                                if i %s %f:
                                    sa += 1
                                else:
                                    sa += 2
                                if %f %s i:
                                    sa += 10000
                                else:
                                    sa += 20000
                                i += 0.25
                            return sa
                    """ % (op1, float(a)/4.0, float(b)/4.0, op2)
                    self.run_and_check(src, threshold=300)

    def test_boolrewrite_ptr(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        compares = ('a == b', 'b == a', 'a != b', 'b != a', 'a == c', 'c != b')
        for e1 in compares:
            for e2 in compares:
                src = """
                    class tst(object):
                        pass
                    def main():
                        a = tst()
                        b = tst()
                        c = tst()
                        sa = 0
                        for i in range(300):
                            if %s:
                                sa += 1
                            else:
                                sa += 2
                            if %s:
                                sa += 10000
                            else:
                                sa += 20000
                            if i > 750:
                                a = b
                        return sa
                """ % (e1, e2)
                self.run_and_check(src, threshold=200)

    def test_array_sum(self):
        def main():
            from array import array
            img = array("i", range(128) * 5) * 480
            l, i = 0, 0
            while i < len(img):
                l += img[i]
                i += 1
            return l
        #
        log = self.run(main, [])
        assert log.result == 19507200
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i13 = int_lt(i7, i9)
            guard_true(i13, descr=<Guard3>)
            i15 = getarrayitem_raw(i10, i7, descr=<.*ArrayNoLengthDescr>)
            i16 = int_add_ovf(i8, i15)
            guard_no_overflow(descr=<Guard4>)
            i18 = int_add(i7, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, p6, i18, i16, i9, i10, descr=<Loop0>)
        """)

    def test_array_intimg(self):
        def main():
            from array import array
            img = array('i', range(3)) * (350 * 480)
            intimg = array('i', (0,)) * (640 * 480)
            l, i = 0, 640
            while i < 640 * 480:
                assert len(img) == 3*350*480
                assert len(intimg) == 640*480
                l = l + img[i]
                intimg[i] = (intimg[i-640] + l)
                i += 1
            return intimg[i - 1]
        #
        log = self.run(main, [])
        assert log.result == 73574560
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i13 = int_lt(i8, 307200)
            guard_true(i13, descr=<Guard3>)
        # the bound check guard on img has been killed (thanks to the asserts)
            i14 = getarrayitem_raw(i10, i8, descr=<.*ArrayNoLengthDescr>)
            i15 = int_add_ovf(i9, i14)
            guard_no_overflow(descr=<Guard4>)
            i17 = int_sub(i8, 640)
        # the bound check guard on intimg has been killed (thanks to the asserts)
            i18 = getarrayitem_raw(i11, i17, descr=<.*ArrayNoLengthDescr>)
            i19 = int_add_ovf(i18, i15)
            guard_no_overflow(descr=<Guard5>)
        # on 64bit, there is a guard checking that i19 actually fits into 32bit
            ...
            setarrayitem_raw(i11, i8, _, descr=<.*ArrayNoLengthDescr>)
            i28 = int_add(i8, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, p6, p7, i28, i15, i10, i11, descr=<Loop0>)
        """)

    def test_func_defaults(self):
        def main(n):
            i = 1
            while i < n:
                i += len(xrange(i+1)) - i
            return i

        log = self.run(main, [10000])
        assert log.result == 10000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i10 = int_lt(i5, i6)
            guard_true(i10, descr=<Guard3>)
            i120 = int_add(i5, 1)
            guard_not_invalidated(descr=<Guard4>)
            --TICK--
            jump(..., descr=<Loop0>)
        """)

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


    def test_intbound_simple(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        ops = ('<', '>', '<=', '>=', '==', '!=')
        nbr = (3, 7)
        for o1 in ops:
            for o2 in ops:
                for n1 in nbr:
                    for n2 in nbr:
                        src = '''
                        def f(i):
                            a, b = 3, 3
                            if i %s %d:
                                a = 0
                            else:
                                a = 1
                            if i %s %d:
                                b = 0
                            else:
                                b = 1
                            return a + b * 2

                        def main():
                            res = [0] * 4
                            idx = []
                            for i in range(15):
                                idx.extend([i] * 15)
                            for i in idx:
                                res[f(i)] += 1
                            return res

                        ''' % (o1, n1, o2, n2)
                        self.run_and_check(src, threshold=200)

    def test_intbound_addsub_mix(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        tests = ('i > 4', 'i > 2', 'i + 1 > 2', '1 + i > 4',
                 'i - 1 > 1', '1 - i > 1', '1 - i < -3',
                 'i == 1', 'i == 5', 'i != 1', '-2 * i < -4')
        for t1 in tests:
            for t2 in tests:
                src = '''
                def f(i):
                    a, b = 3, 3
                    if %s:
                        a = 0
                    else:
                        a = 1
                    if %s:
                        b = 0
                    else:
                        b = 1
                    return a + b * 2

                def main():
                    res = [0] * 4
                    idx = []
                    for i in range(15):
                        idx.extend([i] * 15)
                    for i in idx:
                        res[f(i)] += 1
                    return res

                ''' % (t1, t2)
                self.run_and_check(src, threshold=200)

    def test_intbound_gt(self):
        def main(n):
            i, a, b = 0, 0, 0
            while i < n:
                if i > -1:
                    a += 1
                if i > -2:
                    b += 1
                i += 1
            return (a, b)
        #
        log = self.run(main, [300], threshold=200)
        assert log.result == (300, 300)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i10 = int_lt(i8, i9)
            guard_true(i10, descr=...)
            i12 = int_add_ovf(i7, 1)
            guard_no_overflow(descr=...)
            i14 = int_add_ovf(i6, 1)
            guard_no_overflow(descr=...)
            i17 = int_add(i8, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i14, i12, i17, i9, descr=<Loop0>)
        """)

    def test_intbound_sub_lt(self):
        def main():
            i, a = 0, 0
            while i < 300:
                if i - 10 < 295:
                    a += 1
                i += 1
            return a
        #
        log = self.run(main, [], threshold=200)
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i5, 300)
            guard_true(i7, descr=...)
            i9 = int_sub_ovf(i5, 10)
            guard_no_overflow(descr=...)
            i11 = int_add_ovf(i4, 1)
            guard_no_overflow(descr=...)
            i13 = int_add(i5, 1)
            --TICK--
            jump(p0, p1, p2, p3, i11, i13, descr=<Loop0>)
        """)

    def test_intbound_addsub_ge(self):
        def main(n):
            i, a, b = 0, 0, 0
            while i < n:
                if i + 5 >= 5:
                    a += 1
                if i - 1 >= -1:
                    b += 1
                i += 1
            return (a, b)
        #
        log = self.run(main, [300], threshold=200)
        assert log.result == (300, 300)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i10 = int_lt(i8, i9)
            guard_true(i10, descr=...)
            i12 = int_add_ovf(i8, 5)
            guard_no_overflow(descr=...)
            i14 = int_add_ovf(i7, 1)
            guard_no_overflow(descr=...)
            i16s = int_sub(i8, 1)
            i16 = int_add_ovf(i6, 1)
            guard_no_overflow(descr=...)
            i19 = int_add(i8, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i16, i14, i19, i9, descr=<Loop0>)
        """)

    def test_intbound_addmul_ge(self):
        def main(n):
            i, a, b = 0, 0, 0
            while i < 300:
                if i + 5 >= 5:
                    a += 1
                if 2 * i >= 0:
                    b += 1
                i += 1
            return (a, b)
        #
        log = self.run(main, [300], threshold=200)
        assert log.result == (300, 300)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i10 = int_lt(i8, 300)
            guard_true(i10, descr=...)
            i12 = int_add(i8, 5)
            i14 = int_add_ovf(i7, 1)
            guard_no_overflow(descr=...)
            i16 = int_lshift(i8, 1)
            i18 = int_add_ovf(i6, 1)
            guard_no_overflow(descr=...)
            i21 = int_add(i8, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i18, i14, i21, descr=<Loop0>)
        """)

    def test_intbound_eq(self):
        def main(a, n):
            i, s = 0, 0
            while i < 300:
                if a == 7:
                    s += a + 1
                elif i == 10:
                    s += i
                else:
                    s += 1
                i += 1
            return s
        #
        log = self.run(main, [7, 300], threshold=200)
        assert log.result == main(7, 300)
        log = self.run(main, [10, 300], threshold=200)
        assert log.result == main(10, 300)
        log = self.run(main, [42, 300], threshold=200)
        assert log.result == main(42, 300)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i10 = int_lt(i8, 300)
            guard_true(i10, descr=...)
            i12 = int_eq(i8, 10)
            guard_false(i12, descr=...)
            i14 = int_add_ovf(i7, 1)
            guard_no_overflow(descr=...)
            i16 = int_add(i8, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, p6, i14, i16, descr=<Loop0>)
        """)

    def test_intbound_mul(self):
        def main(a):
            i, s = 0, 0
            while i < 300:
                assert i >= 0
                if 2 * i < 30000:
                    s += 1
                else:
                    s += a
                i += 1
            return s
        #
        log = self.run(main, [7], threshold=200)
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i8 = int_lt(i6, 300)
            guard_true(i8, descr=...)
            i10 = int_lshift(i6, 1)
            i12 = int_add_ovf(i5, 1)
            guard_no_overflow(descr=...)
            i14 = int_add(i6, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, i12, i14, descr=<Loop0>)
        """)

    def test_assert(self):
        def main(a):
            i, s = 0, 0
            while i < 300:
                assert a == 7
                s += a + 1
                i += 1
            return s
        log = self.run(main, [7], threshold=200)
        assert log.result == 300*8
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i8 = int_lt(i6, 300)
            guard_true(i8, descr=...)
            i10 = int_add_ovf(i5, 8)
            guard_no_overflow(descr=...)
            i12 = int_add(i6, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, i10, i12, descr=<Loop0>)
        """)

    def test_zeropadded(self):
        def main():
            from array import array
            class ZeroPadded(array):
                def __new__(cls, l):
                    self = array.__new__(cls, 'd', range(l))
                    return self

                def __getitem__(self, i):
                    if i < 0 or i >= len(self):
                        return 0
                    return array.__getitem__(self, i) # ID: get
            #
            buf = ZeroPadded(2000)
            i = 10
            sa = 0
            while i < 2000 - 10:
                sa += buf[i-2] + buf[i-1] + buf[i] + buf[i+1] + buf[i+2]
                i += 1
            return sa

        log = self.run(main, [], threshold=200)
        assert log.result == 9895050.0
        loop, = log.loops_by_filename(self.filepath)
        #
        # check that the overloaded __getitem__ does not introduce double
        # array bound checks.
        #
        # The force_token()s are still there, but will be eliminated by the
        # backend regalloc, so they are harmless
        assert loop.match(ignore_ops=['force_token'],
                          expected_src="""
            ...
            i20 = int_ge(i18, i8)
            guard_false(i20, descr=...)
            f21 = getarrayitem_raw(i13, i18, descr=...)
            i14 = int_sub(i6, 1)
            i15 = int_ge(i14, i8)
            guard_false(i15, descr=...)
            f23 = getarrayitem_raw(i13, i14, descr=...)
            f24 = float_add(f21, f23)
            f26 = getarrayitem_raw(i13, i6, descr=...)
            f27 = float_add(f24, f26)
            i29 = int_add(i6, 1)
            i31 = int_ge(i29, i8)
            guard_false(i31, descr=...)
            f33 = getarrayitem_raw(i13, i29, descr=...)
            f34 = float_add(f27, f33)
            i36 = int_add(i6, 2)
            i38 = int_ge(i36, i8)
            guard_false(i38, descr=...)
            f39 = getarrayitem_raw(i13, i36, descr=...)
            ...
        """)


    def test_circular(self):
        def main():
            from array import array
            class Circular(array):
                def __new__(cls):
                    self = array.__new__(cls, 'd', range(256))
                    return self
                def __getitem__(self, i):
                    assert len(self) == 256
                    return array.__getitem__(self, i & 255)
            #
            buf = Circular()
            i = 10
            sa = 0
            while i < 2000 - 10:
                sa += buf[i-2] + buf[i-1] + buf[i] + buf[i+1] + buf[i+2]
                i += 1
            return sa
        #
        log = self.run(main, [], threshold=200)
        assert log.result == 1239690.0
        loop, = log.loops_by_filename(self.filepath)
        #
        # check that the array bound checks are removed
        #
        # The force_token()s are still there, but will be eliminated by the
        # backend regalloc, so they are harmless
        assert loop.match(ignore_ops=['force_token'],
                          expected_src="""
            ...
            i17 = int_and(i14, 255)
            f18 = getarrayitem_raw(i8, i17, descr=...)
            i19s = int_sub_ovf(i6, 1)
            guard_no_overflow(descr=...)
            i22s = int_and(i19s, 255)
            f20 = getarrayitem_raw(i8, i22s, descr=...)
            f21 = float_add(f18, f20)
            f23 = getarrayitem_raw(i8, i10, descr=...)
            f24 = float_add(f21, f23)
            i26 = int_add(i6, 1)
            i29 = int_and(i26, 255)
            f30 = getarrayitem_raw(i8, i29, descr=...)
            f31 = float_add(f24, f30)
            i33 = int_add(i6, 2)
            i36 = int_and(i33, 255)
            f37 = getarrayitem_raw(i8, i36, descr=...)
            ...
        """)

    def test_min_max(self):
        def main():
            i=0
            sa=0
            while i < 300:
                sa+=min(max(i, 3000), 4000)
                i+=1
            return sa
        log = self.run(main, [], threshold=200)
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
        log = self.run(main, [], threshold=200)
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
        log = self.run(main, [], threshold=200)
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
                res += pow(2, 3)
                i += 1
            return pow.getaddr(), res
        #
        libm_name = get_libm_name(sys.platform)
        log = self.run(main, [libm_name], threshold=200)
        pow_addr, res = log.result
        assert res == 8.0 * 300
        loop, = log.loops_by_filename(self.filepath)
        # XXX: write the actual test when we merge this to jitypes2
        ## ops = self.get_by_bytecode('CALL_FUNCTION')
        ## assert len(ops) == 2 # we get two loops, because of specialization
        ## call_function = ops[0]
        ## last_ops = [op.getopname() for op in call_function[-5:]]
        ## assert last_ops == ['force_token',
        ##                     'setfield_gc',
        ##                     'call_may_force',
        ##                     'guard_not_forced',
        ##                     'guard_no_exception']
        ## call = call_function[-3]
        ## assert call.getarg(0).value == pow_addr
        ## assert call.getarg(1).value == 2.0
        ## assert call.getarg(2).value == 3.0

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

        log = self.run(main, [11], threshold=200)
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

        log = self.run(main, [9], threshold=200)
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        # we don't know that b>10, hence we cannot optimize it
        assert loop.match_by_id('guard', """
            i10 = int_xor(i5, i7)
            i12 = int_ge(i10, 0)
            guard_true(i12, descr=...)
        """)

    def test_shift_intbound(self):
        def main(b):
            res = 0
            a = 0
            while a < 300:
                assert a >= 0
                assert 0 <= b <= 10
                val = a >> b
                if val >= 0:    # ID: rshift
                    res += 1
                val = a << b
                if val >= 0:    # ID: lshift
                    res += 2
                a += 1
            return res
        #
        log = self.run(main, [2], threshold=200)
        assert log.result == 300*3
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('rshift', "")  # guard optimized away
        assert loop.match_by_id('lshift', "")  # guard optimized away

    def test_lshift_and_then_rshift(self):
        py.test.skip('fixme, this optimization is disabled')
        def main(b):
            res = 0
            a = 0
            while res < 300:
                assert a >= 0
                assert 0 <= b <= 10
                res = (a << b) >> b     # ID: shift
                a += 1
            return res
        #
        log = self.run(main, [2], threshold=200)
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('shift', "")  # optimized away

    def test_division_to_rshift(self):
        py.test.skip('in-progress')
        def main(b):
            res = 0
            a = 0
            while a < 300:
                assert a >= 0
                assert 0 <= b <= 10
                res = a/b     # ID: div
                a += 1
            return res
        #
        log = self.run(main, [3], threshold=200)
        #assert log.result == 149
        loop, = log.loops_by_filename(self.filepath)
        import pdb;pdb.set_trace()
        assert loop.match_by_id('div', "")  # optimized away

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
        loop.match_by_id('loadattr',
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

            log = self.run(main, [], threshold=80)
            loop, = log.loops_by_filename(self.filemath)
            # XXX: haven't confirmed his is correct, it's probably missing a
            # few instructions
            loop.match_by_id("contains", """
                i1 = int_add(i0, 1)
            """)
