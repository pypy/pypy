import sys
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

if sys.maxint == 2147483647:
    SHIFT = 31
else:
    SHIFT = 63

# XXX review the <Call> descrs to replace some EF=4 with EF=3 (elidable)


class TestString(BaseTestPyPyC):
    def test_lookup_default_encoding(self):
        def main(n):
            import string
            i = 0
            letters = string.letters
            uletters = unicode(string.letters)
            while i < n:
                i += letters[i % len(letters)] == uletters[i % len(letters)]
            return i

        log = self.run(main, [300], import_site=True)
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i14 = int_lt(i6, i9)
            guard_true(i14, descr=...)
            guard_not_invalidated(descr=...)
            i16 = int_eq(i6, %d)
            guard_false(i16, descr=...)
            i15 = int_mod(i6, i10)
            i17 = int_rshift(i15, %d)
            i18 = int_and(i10, i17)
            i19 = int_add(i15, i18)
            i21 = int_lt(i19, 0)
            guard_false(i21, descr=...)
            i22 = int_ge(i19, i10)
            guard_false(i22, descr=...)
            i23 = strgetitem(p11, i19)
            i24 = int_ge(i19, i12)
            guard_false(i24, descr=...)
            i25 = unicodegetitem(p13, i19)
            p27 = newstr(1)
            strsetitem(p27, 0, i23)
            p30 = call(ConstClass(ll_str2unicode__rpy_stringPtr), p27, descr=...)
            guard_no_exception(descr=...)
            i32 = call(ConstClass(_ll_2_str_eq_checknull_char__rpy_unicodePtr_UniChar), p30, i25, descr=...)
            guard_true(i32, descr=...)
            i34 = int_add(i6, 1)
            --TICK--
            jump(..., descr=...)
        """ % (-sys.maxint-1, SHIFT))

    def test_long(self):
        def main(n):
            import string
            i = 1
            while i < n:
                i += int(long(string.digits[i % len(string.digits)], 16))
            return i

        log = self.run(main, [1100], import_site=True)
        assert log.result == main(1100)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i11 = int_lt(i6, i7)
            guard_true(i11, descr=...)
            guard_not_invalidated(descr=...)
            i13 = int_eq(i6, %d)         # value provided below
            guard_false(i13, descr=...)
            i15 = int_mod(i6, 10)
            i17 = int_rshift(i15, %d)    # value provided below
            i18 = int_and(10, i17)
            i19 = int_add(i15, i18)
            i21 = int_lt(i19, 0)
            guard_false(i21, descr=...)
            i22 = int_ge(i19, 10)
            guard_false(i22, descr=...)
            i23 = strgetitem(p10, i19)
            p25 = newstr(1)
            strsetitem(p25, 0, i23)
            p93 = call(ConstClass(fromstr), p25, 16, descr=<Callr . ri EF=3>)
            guard_no_exception(descr=...)
            i95 = getfield_gc_pure(p93, descr=<FieldS rpython.rlib.rbigint.rbigint.inst_size .*>)
            i96 = int_gt(i95, #)
            guard_false(i96, descr=...)
            i94 = call(ConstClass(rbigint._toint_helper), p93, descr=<Calli . r EF=3>)
            guard_no_exception(descr=...)
            i95 = int_add_ovf(i6, i94)
            guard_no_overflow(descr=...)
            --TICK--
            jump(..., descr=...)
        """ % (-sys.maxint-1, SHIFT))

    def test_str_mod(self):
        def main(n):
            s = 0
            while n > 0:
                s += len('%d %d' % (n, n))
                n -= 1
            return s

        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i79 = int_gt(i74, 0)
            guard_true(i79, descr=...)
            guard_not_invalidated(descr=...)
            p80 = call(ConstClass(ll_int2dec__Signed), i74, descr=<Callr . i EF=3>)
            guard_no_exception(descr=...)
            i85 = strlen(p80)
            p86 = new(descr=<SizeDescr .+>)
            p88 = newstr(23)
            {{{
            setfield_gc(p86, 0, descr=<FieldS stringbuilder.current_pos .+>)
            setfield_gc(p86, p88, descr=<FieldP stringbuilder.current_buf .+>)
            setfield_gc(p86, 23, descr=<FieldS stringbuilder.current_end .+>)
            setfield_gc(p86, 23, descr=<FieldS stringbuilder.total_size .+>)
            }}}
            call(ConstClass(ll_append_res0__stringbuilderPtr_rpy_stringPtr), p86, p80, descr=<Callv 0 rr EF=4>)
            guard_no_exception(descr=...)
            i89 = getfield_gc(p86, descr=<FieldS stringbuilder.current_pos .+>)
            i90 = getfield_gc(p86, descr=<FieldS stringbuilder.current_end .+>)
            i91 = int_eq(i89, i90)
            cond_call(i91, ConstClass(ll_grow_by__stringbuilderPtr_Signed), p86, 1, descr=<Callv 0 ri EF=4>)
            guard_no_exception(descr=...)
            i92 = getfield_gc(p86, descr=<FieldS stringbuilder.current_pos .+>)
            i93 = int_add(i92, 1)
            p94 = getfield_gc(p86, descr=<FieldP stringbuilder.current_buf .+>)
            strsetitem(p94, i92, 32)
            setfield_gc(p86, i93, descr=<FieldS stringbuilder.current_pos .+>)
            call(ConstClass(ll_append_res0__stringbuilderPtr_rpy_stringPtr), p86, p80, descr=<Callv 0 rr EF=4>)
            guard_no_exception(descr=...)
            p95 = call(..., descr=<Callr . r EF=4>)     # ll_build
            guard_no_exception(descr=...)
            i96 = strlen(p95)
            i97 = int_add_ovf(i71, i96)
            guard_no_overflow(descr=...)
            i98 = int_sub(i74, 1)
            --TICK--
            jump(..., descr=...)
        """)

    def test_getattr_promote(self):
        def main(n):
            class A(object):
                def meth_a(self):
                    return 1
                def meth_b(self):
                    return 2
            a = A()

            l = ['a', 'b']
            s = 0
            for i in range(n):
                name = 'meth_' + l[i & 1]
                meth = getattr(a, name) # ID: getattr
                s += meth()
            return s

        log = self.run(main, [1000])
        assert log.result == main(1000)
        loops = log.loops_by_filename(self.filepath)
        assert len(loops) == 1
        for loop in loops:
            assert loop.match_by_id('getattr','''
            guard_not_invalidated?
            i32 = strlen(p31)
            i34 = int_add(5, i32)
            p35 = newstr(i34)
            strsetitem(p35, 0, 109)
            strsetitem(p35, 1, 101)
            strsetitem(p35, 2, 116)
            strsetitem(p35, 3, 104)
            strsetitem(p35, 4, 95)
            copystrcontent(p31, p35, 0, 5, i32)
            i49 = call(ConstClass(_ll_2_str_eq_nonnull__rpy_stringPtr_rpy_stringPtr), p35, ConstPtr(ptr48), descr=<Calli [48] rr EF=0 OS=28>)
            guard_value(i49, 1, descr=...)
            ''')

    def test_remove_duplicate_method_calls(self):
        def main(n):
            lst = []
            for i in range(n):
                s = 'Hello %d' % i
                t = s.lower()   # ID: callone
                u = s.lower()   # ID: calltwo
                lst.append(t)
                lst.append(u)
            return len(','.join(lst))
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loops = log.loops_by_filename(self.filepath)
        loop, = loops
        assert loop.match_by_id('callone', '''
            p114 = call(ConstClass(ll_lower__rpy_stringPtr), p113, descr=<Callr . r EF=3>)
            guard_no_exception(descr=...)
            ''')
        assert loop.match_by_id('calltwo', '')    # nothing

    def test_move_method_call_out_of_loop(self):
        def main(n):
            lst = []
            s = 'Hello %d' % n
            for i in range(n):
                t = s.lower()   # ID: callone
                lst.append(t)
            return len(','.join(lst))
        log = self.run(main, [1000])
        assert log.result == main(1000)
        loops = log.loops_by_filename(self.filepath)
        loop, = loops
        assert loop.match_by_id('callone', '')    # nothing

    def test_lookup_codec(self):
        log = self.run("""
        import codecs

        def main(n):
            for i in xrange(n):
                codecs.lookup('utf8')
            return i
        """, [1000])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
        i45 = int_lt(i43, i26)
        guard_true(i45, descr=...)
        i46 = int_add(i43, 1)
        setfield_gc(p15, i46, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current 8>)
        guard_not_invalidated(descr=...)
        --TICK--
        jump(..., descr=...)
        """)

    def test_decode_ascii(self):
        log = self.run("""
        def main(n):
            for i in xrange(n):
                unicode('abc')
            return i
        """, [1000])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
        i49 = int_lt(i47, i24)
        guard_true(i49, descr=...)
        i50 = int_add(i47, 1)
        setfield_gc(p15, i50, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current 8>)
        guard_not_invalidated(descr=...)
        p52 = call(ConstClass(str_decode_ascii__raise_unicode_exception_decode), ConstPtr(ptr38), 3, 1, descr=<Callr . rii EF=4>)
        guard_no_exception(descr=...)
        p53 = getfield_gc_pure(p52, descr=<FieldP tuple2.item0 .>)
        guard_nonnull(p53, descr=...)
        --TICK--
        jump(..., descr=...)
        """)
