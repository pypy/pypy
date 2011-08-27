import py
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

class TestInstance(BaseTestPyPyC):

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
            guard_true(i7, descr=...)
            guard_not_invalidated(descr=...)
            i9 = int_add_ovf(i5, 2)
            guard_no_overflow(descr=...)
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
            guard_true(i9, descr=...)
            guard_not_invalidated(descr=...)
            i10 = int_add_ovf(i5, i7)
            guard_no_overflow(descr=...)
            --TICK--
            jump(p0, p1, p2, p3, p4, i10, i6, i7, p8, descr=<Loop0>)
        """)

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
            i8 = getfield_gc_pure(p5, descr=...)
            i9 = int_lt(i8, i7)
            guard_true(i9, descr=.*)
            guard_not_invalidated(descr=.*)
            i82 = getfield_gc_pure(p8, descr=...)
            i11 = int_add_ovf(i82, 1)
            guard_no_overflow(descr=...)
            i12 = force_token()
            --TICK--
            p20 = new_with_vtable(ConstClass(W_IntObject))
            setfield_gc(p20, i11, descr=<SignedFieldDescr.*W_IntObject.inst_intval .*>)
            setfield_gc(ConstPtr(ptr21), p20, descr=<GcPtrFieldDescr .*TypeCell.inst_w_value .*>)
            jump(p0, p1, p2, p3, p4, p20, p6, i7, p20, descr=<Loop.>)
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
        i16 = arraylen_gc(p10, descr=<GcPtrArrayDescr>)
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

