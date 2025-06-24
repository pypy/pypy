from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestDicts(BaseTestPyPyC):
    def test_strdict(self):
        def fn(n):
            import sys
            d = {}
            class A(object):
                pass
            a = A()
            a.x = "x" # stop field unboxing
            a.x = 1
            for s in sys.modules.keys() * 1000:
                d.get(s)  # force pending setfields etc.
                inc = a.x # ID: look
                d[s] = d.get(s, 0) + inc
            return sum(d.values())
        #
        log = self.run(fn, [1000])
        assert log.result % 1000 == 0
        loop, = log.loops_by_filename(self.filepath)
        ops = loop.ops_by_id('look')
        assert log.opnames(ops) == ['guard_nonnull_class']

    def test_identitydict(self):
        def fn(n):
            class X(object):
                pass
            x = X()
            d = {}
            d[x] = 1
            res = 0
            for i in range(300):
                value = d[x]  # ID: getitem
                res += value
            return res
        #
        log = self.run(fn, [1000])
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        # check that the call to ll_dict_lookup is not a call_may_force, the
        # gc_id call is hoisted out of the loop, the id of a value obviously
        # can't change ;)
        assert loop.match_by_id("getitem", """
            ...
            i26 = call_i(ConstClass(ll_call_lookup_function), p18, p6, i25, 0, descr=...)
            ...
            p33 = getinteriorfield_gc_r(p31, i26, descr=<InteriorFieldDescr <FieldP odictentry.value .*>>)
            ...
        """)

    def test_non_virtual_dict(self):
        def main(n):
            i = 0
            while i < n:
                d = {str(i): i}
                i += d[str(i)] - i + 1
            return i

        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i8 = int_lt(i5, i7)
            guard_true(i8, descr=...)
            guard_not_invalidated(descr=...)
            p10 = call_r(ConstClass(ll_str__IntegerR_SignedConst_Signed), i5, descr=<Callr . i EF=3>)
            guard_no_exception(descr=...)
            guard_nonnull(p10, descr=...)
            i99 = strhash(p10)
            i12 = cond_call_value_i(i99, ConstClass(_ll_strhash__rpy_stringPtr), p10, descr=<Calli . r EF=2>)
            p13 = new(descr=...)
            p15 = new_array_clear(16, descr=<ArrayU 1>)
            {{{
            setfield_gc(p13, 0, descr=<FieldS dicttable.num_ever_used_items .+>)
            setfield_gc(p13, p15, descr=<FieldP dicttable.indexes .+>)
            setfield_gc(p13, ConstPtr(0), descr=<FieldP dicttable.entries .+>)
            }}}
            i17 = call_i(ConstClass(ll_dict_lookup_trampoline), p13, p10, i12, 1, descr=<Calli . rrii EF=5 OS=4>)
            {{{
            setfield_gc(p13, 0, descr=<FieldS dicttable.lookup_function_no .+>)
            setfield_gc(p13, 0, descr=<FieldS dicttable.num_live_items .+>)
            setfield_gc(p13, 32, descr=<FieldS dicttable.resize_counter .+>)
            }}}
            guard_no_exception(descr=...)
            p20 = new_with_vtable(descr=...)
            call_n(ConstClass(_ll_dict_setitem_lookup_done_trampoline), p13, p10, p20, i12, i17, descr=<Callv 0 rrrii EF=5>)
            setfield_gc(p20, i5, descr=<FieldS .*W_IntObject.inst_intval .* pure>)
            guard_no_exception(descr=...)
            i98 = strhash(p10)
            i23 = call_i(ConstClass(ll_call_lookup_function), p13, p10, i12, 0, descr=<Calli . rrii EF=5 OS=4>)
            guard_no_exception(descr=...)
            i27 = int_lt(i23, 0)
            guard_false(i27, descr=...)
            p28 = getfield_gc_r(p13, descr=<FieldP dicttable.entries .*>)
            p29 = getinteriorfield_gc_r(p28, i23, descr=<InteriorFieldDescr <FieldP odictentry.value .*>>)
            guard_nonnull_class(p29, ConstClass(W_IntObject), descr=...)
            i31 = getfield_gc_i(p29, descr=<FieldS .*W_IntObject.inst_intval .* pure>)
            i32 = int_sub_ovf(i31, i5)
            guard_no_overflow(descr=...)
            i34 = int_add_ovf(i32, 1)
            guard_no_overflow(descr=...)
            i35 = int_add_ovf(i5, i34)
            guard_no_overflow(descr=...)
            --TICK--
            jump(..., descr=...)
        """)



class TestOtherContainers(BaseTestPyPyC):
    def test_list(self):
        def main(n):
            i = 0
            while i < n:
                z = list(())
                z.append(1)
                i += z[-1] / len(z)
            return i

        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i5, i6)
            guard_true(i7, descr=...)
            guard_not_invalidated(descr=...)
            i9 = int_add(i5, 1)
            --TICK--
            jump(..., descr=...)
        """)

    def test_floatlist_unpack_without_calls(self):
        def fn(n):
            l = [2.3, 3.4, 4.5]
            for i in range(n):
                x, y, z = l # ID: look
        #
        log = self.run(fn, [1000])
        loop, = log.loops_by_filename(self.filepath)
        ops = loop.ops_by_id('look')
        assert 'call' not in log.opnames(ops)

    # XXX the following tests only work with strategies enabled
    def test_should_not_create_intobject_with_sets(self):
        def main(n):
            i = 0
            s = set()
            while i < n:
                s.add(i)
                i += 1
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_should_not_create_stringobject_with_sets(self):
        def main(n):
            i = 0
            s = set()
            while i < n:
                s.add(str(i))
                i += 1
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_should_not_create_intobject_with_lists(self):
        def main(n):
            i = 0
            l = []
            while i < n:
                l.append(i)
                i += 1
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_should_not_create_stringobject_with_lists(self):
        def main(n):
            i = 0
            l = []
            while i < n:
                l.append(str(i))
                i += 1
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_optimized_create_list_from_string(self):
        def main(n):
            i = 0
            l = []
            while i < n:
                l = list("abc" * i)
                i += 1
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_optimized_create_set_from_list(self):
        def main(n):
            i = 0
            while i < n:
                s = set([1, 2, 3])
                i += 1
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_constfold_tuple(self):
        code = """if 1:
        tup = tuple(range(10000))
        l = [1, 2, 3, 4, 5, 6, "a"]
        def main(n):
            while n > 0:
                sub = tup[1]  # ID: getitem
                l[1] = n # kill cache of tup[1]
                n -= sub
        """
        log = self.run(code, [1000])
        loop, = log.loops_by_filename(self.filepath)
        ops = loop.ops_by_id('getitem', include_guard_not_invalidated=False)
        assert log.opnames(ops) == []


    def test_specialised_tuple(self):
        def main(n):
            import pypyjit

            f = lambda: None
            tup = (n, n)
            while n > 0:
                tup[0]  # ID: getitem
                pypyjit.residual_call(f)
                n -= 1

        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        ops = loop.ops_by_id('getitem', include_guard_not_invalidated=False)
        assert log.opnames(ops) == []

    def test_enumerate_list(self):
        def main(n):
            for a, b in enumerate([1, 2] * 1000):
                a + b

        log = self.run(main, [1000])
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_enumerate(self):
        def main(n):
            for a, b in enumerate("abc" * 1000):
                a + ord(b)

        log = self.run(main, [1000])
        loop, = log.loops_by_filename(self.filepath)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0

    def test_unpack_list(self):
        def main():
            l = [1, 4, 6]
            for x in range(10000):
                a, b, c = l # ID: unpack
                a, b, c = l
                a, b, c = l
        log = self.run(main, [])
        loop, = log.loops_by_id("unpack", is_entry_bridge=True)
        opnames = log.opnames(loop.allops())
        assert opnames.count('new_with_vtable') == 0
        assert opnames.count('new_array_clear') == 0

    def test_count_doesnt_escape_w_list(self):
        def main():
            l0 = [1, 4, 6]
            res = 0
            for x in range(10000):
                l = list(l0)
                res += l.count(4) # ID: count

        log = self.run(main, [])
        loop, = log.loops_by_id("count")
        ops = loop.ops_by_id("count")
        opnames = log.opnames(ops)
        assert "new_with_vtable" not in opnames

    def test_cache_varindex_from_list(self):
        def main():
            l = [1, 2, 3]
            res = 0
            for i in range(10000):
                index = i % 3
                res += l[index] + l[index] # ID: getitem
            return res
        log = self.run(main, [])
        loop, = log.loops_by_filename(self.filepath)
        loop.match_by_id('getitem', '''
        setfield_gc(p18, i69, descr=...) # part of the for loop
        i77 = uint_ge(i76, i53)
        guard_false(i77, descr=...)
        i79 = getarrayitem_gc_i(p55, i76, descr=...) # only a single getarrayitem
        i80 = int_add_ovf(i79, i79)
        guard_no_overflow(descr=...)
        i81 = int_add_ovf(i59, i80)
        guard_no_overflow(descr=...)
        --TICK--
        ''')

    def test_cache_varindex_from_list_write(self):
        def main():
            l = [1, 2, 3]
            res = 0
            for i in range(10000):
                index = i % 3
                l[index] += 1
                res += l[index] # ID: getitem
            return res
        log = self.run(main, [])
        loop, = log.loops_by_filename(self.filepath)
        loop.match_by_id('getitem', '''
        i83 = int_add_ovf(i60, i82)
        guard_no_overflow(descr=...)
        --TICK--
        ''')

    def test_list_aliasing_via_length(self):
        def main():
            import __pypy__
            l = [1, 2, 3]
            l2 = [4, 5, 6, 7, 8]
            l3 = [4, 5, 6, 7, 8]
            list_of_list = [l2, l3]
            res = 0
            for i in range(1000):
                l2 = list_of_list[i & 1]
                assert __pypy__.list_get_physical_size(l2) == 5
                res += l2[0]
                assert __pypy__.list_get_physical_size(l) == 3
                l[0] += 1 # can't affect l2 because the length is different
                # reuse previous result in next line
                res += l2[0] # ID: getitem2
            return res
        log = self.run(main, [])
        loop, = log.loops_by_filename(self.filepath)
        loop.match_by_id('getitem2', '''
        setarrayitem_gc(p82, 0, i125, descr=...) # delayed write to l
        i83 = int_add_ovf(i60, i82) # no second read from l2
        guard_no_overflow(descr=...)
        --TICK--
        ''')

    def test_dict_values_single_copy(self):
        def main():
            res = 0
            d = {"a": None, "b": object, "c": type, "d": True}
            for i in range(100000):
                l = d.values() # ID: list
                res += len(l)

        log = self.run(main, [])
        loop, = log.loops_by_id("list")
        ops = loop.ops_by_id("list")
        opnames = log.opnames(ops)
        # only a call to ll_kvi, not to get_strategy_from_list_objects
        assert opnames.count("call_r") == 1

    def test_list_eq(self):
        def main():
            l1 = [i * 3 + 1 for i in range(10000)]
            l2 = [i * 3 + 1 for i in range(10000)]
            return l1 == l2
        log = self.run(main, [])
        loop = log._filter(log.loops[-1], is_entry_bridge=False)
        loop.match("""
        i22 = uint_ge(i19, i6)
        guard_false(i22, descr=...)
        i23 = getarrayitem_gc_i(p8, i19, descr=...)
        i24 = uint_ge(i19, i13)
        guard_false(i24, descr=...)
        i25 = getarrayitem_gc_i(p15, i19, descr=...)
        i26 = int_eq(i25, i23)
        guard_true(i26, descr=...)
        i28 = int_add(i19, 1)
        i29 = int_lt(i28, i6)
        guard_true(i29, descr=...)
        i30 = int_lt(i28, i13)
        guard_true(i30, descr=...)
        i31 = arraylen_gc(p8, descr=...)
        i32 = arraylen_gc(p15, descr=...)
        jump(i28, p1, p2, p5, i6, p8, p12, i13, p15, descr=...)""")
