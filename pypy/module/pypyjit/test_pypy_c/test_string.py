# -*- coding: utf-8 -*-
import sys
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

# XXX review the <Call> descrs to replace some EF=5 with EF=4 (elidable)


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
            i83 = call_i(ConstClass(ll_int_py_mod__Signed_Signed), i6, i10, descr=<Calli . ii EF=0 OS=14>)
            i21 = int_lt(i83, 0)
            guard_false(i21, descr=...)
            i22 = int_ge(i83, i10)
            guard_false(i22, descr=...)
            i89 = strgetitem(p55, i83)
            i24 = int_ge(i83, i12)
            guard_false(i24, descr=...)
            i93 = int_add(i83, 1)
            i94 = int_gt(i93, i56)
            guard_false(i94, descr=...)
            p96 = newstr(1)
            strsetitem(p96, 0, i89)
            i98 = call_i(ConstClass(first_non_ascii_char), p96, descr=<Calli . r EF=4>)
            guard_no_exception(descr=...)
            i100 = int_lt(i98, 0)
            guard_true(i100, descr=...)
            i102 = call_i(ConstClass(_ll_4_str_eq_slice_char__rpy_stringPtr_Signed_Signed_Char), p13, i83, 1, i89, descr=<Calli . riii EF=0 OS=27>)
            guard_true(i102, descr=...)
            i104 = int_add(i6, 1)
            --TICK--
            jump(..., descr=...)
        """ % (-sys.maxint-1,))

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
        if sys.maxint > 2**32:
            args = (63, -3689348814741910323, 3)
        else:
            args = (31, -858993459, 3)
        assert loop.match("""
            i11 = int_lt(i6, i7)
            guard_true(i11, descr=...)
            guard_not_invalidated(descr=...)
            i13 = int_eq(i6, %d)         # value provided below

            # "mod 10" block:
            i79 = int_rshift(i6, %d)
            i80 = int_xor(i6, i79)
            i82 = uint_mul_high(i80, %d)
            i84 = uint_rshift(i82, %d)
            i85 = int_xor(i84, i79)
            i87 = int_mul(i85, 10)
            i19 = int_sub(i6, i87)

            i23 = strgetitem(p10, i19)
            p25 = newstr(1)
            strsetitem(p25, 0, i23)
            p93 = call_r(ConstClass(fromstr), p25, 16, 0, descr=<Callr . rii EF=4>)
            guard_no_exception(descr=...)
            i95 = getfield_gc_i(p93, descr=<FieldS rpython.rlib.rbigint.rbigint.inst_size .*>)
            i96 = int_gt(i95, #)
            guard_false(i96, descr=...)
            i94 = call_i(ConstClass(rbigint._toint_helper), p93, descr=<Calli . r EF=4>)
            guard_no_exception(descr=...)
            i95 = int_add_ovf(i6, i94)
            guard_no_overflow(descr=...)
            --TICK--
            jump(..., descr=...)
        """ % ((-sys.maxint-1,)+args))

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
            p80 = call_r(ConstClass(ll_int2dec__Signed), i74, descr=<Callr . i EF=3>)
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
            call_n(ConstClass(ll_append_res0__stringbuilderPtr_rpy_stringPtr), p86, p80, descr=<Callv 0 rr EF=5>)
            guard_no_exception(descr=...)
            i89 = getfield_gc_i(p86, descr=<FieldS stringbuilder.current_pos .+>)
            i90 = getfield_gc_i(p86, descr=<FieldS stringbuilder.current_end .+>)
            i91 = int_eq(i89, i90)
            cond_call(i91, ConstClass(ll_grow_by__stringbuilderPtr_Signed), p86, 1, descr=<Callv 0 ri EF=5>)
            guard_no_exception(descr=...)
            i92 = getfield_gc_i(p86, descr=<FieldS stringbuilder.current_pos .+>)
            i93 = int_add(i92, 1)
            p94 = getfield_gc_r(p86, descr=<FieldP stringbuilder.current_buf .+>)
            strsetitem(p94, i92, 32)
            setfield_gc(p86, i93, descr=<FieldS stringbuilder.current_pos .+>)
            call_n(ConstClass(ll_append_res0__stringbuilderPtr_rpy_stringPtr), p86, p80, descr=<Callv 0 rr EF=5>)
            guard_no_exception(descr=...)
            p95 = call_r(..., descr=<Callr . r EF=5>)     # ll_build
            guard_no_exception(descr=...)
            i96 = strlen(p95)
            i97 = int_add_ovf(i71, i96)
            guard_no_overflow(descr=...)
            i98 = int_sub(i74, 1)
            --TICK--
            jump(..., descr=...)
        """)

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
            p114 = call_r(ConstClass(ll_lower__rpy_stringPtr), p113, descr=<Callr . r EF=3>)
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
                unicode(str(i))
            return i
        """, [1000])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
        i49 = int_lt(i47, i24)
        guard_true(i49, descr=...)
        i50 = int_add(i47, 1)
        setfield_gc(p15, i50, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current 8>)
        guard_not_invalidated(descr=...)
        p80 = call_r(ConstClass(ll_str__IntegerR_SignedConst_Signed), i47, descr=<Callr . i EF=3>)
        guard_no_exception(descr=...)
        i51 = call_i(ConstClass(first_non_ascii_char), p80, descr=<Calli . r EF=4>)
        guard_no_exception(descr=...)
        i52 = int_lt(i51, 0)
        guard_true(i52, descr=...)
        i53 = strlen(p80)
        --TICK--
        jump(..., descr=...)
        """)

    def test_unicode_indexing_makes_no_bridges(self):
        log = self.run("""
        b = b"b'aaaaa\xc3\xa4\xf0\x9f\x91\xa9\xe2\x80\x8d\xf0\x9f\x91\xa9\xe2\x80\x8d\xf0\x9f\x91\xa7\xe2\x80\x8d\xf0\x9f\x91\xa6'"
        u = b.decode("utf-8") * 1000
        def main():
            for j in range(10):
                for i in range(len(u)):
                    u[i] # ID: index0
        """, [])
        ops = log.loops[0].ops_by_id("index0")
        for op in ops:
            assert op.bridge is None

    def test_unicode_indexing_small_constant_indices(self):
        log = self.run("""
        l = [u"abä", u"cdä", u"äü", u"éé", u"–—¿"] * 1000
        def main(n):
            global s
            for u in l:
                s = u[0] + u[1] + u[-1] # ID: index
                len(u)
            return len(s)
        """, [1000])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('index', '''
            i77 = getfield_gc_i(p73, descr=<FieldS pypy.objspace.std.unicodeobject.W_UnicodeObject.inst__length .*>)
            p78 = getfield_gc_r(p73, descr=<FieldP pypy.objspace.std.unicodeobject.W_UnicodeObject.inst__utf8 .* pure>)
            i79 = strlen(p78)
            i80 = int_eq(i77, i79)
            guard_false(i80, descr=...) # check not ascii
            i82 = int_ge(0, i77)
            guard_false(i82, descr=...)
            i85 = call_i(ConstClass(next_codepoint_pos_dont_look_inside), p78, 0, descr=...)
            i86 = int_gt(i85, i79)
            guard_false(i86, descr=...)
            i88 = int_ge(1, i77)
            guard_false(i88, descr=...)
            i90 = call_i(ConstClass(next_codepoint_pos_dont_look_inside), p78, i85, descr=...)
            i91 = int_gt(i90, i79)
            guard_false(i91, descr=...)
            i92 = int_sub(i90, i85)
            i94 = int_add(-1, i77)
            i96 = call_i(ConstClass(prev_codepoint_pos_dont_look_inside), p78, i79, descr=...)
            i97 = int_sub(i79, i96)
            guard_not_invalidated(descr=...)
        ''')

    def test_unicode_slicing_small_constant_indices(self):
        log = self.run("""
        def main(n):
            b = b'ab\xc3\xa4\xf0\x9f\x91\xa9\xe2\x80\x8d\xf0\x9f\x91\xa9\xe2\x80\x8d\xf0\x9f\x91\xa7\xe2\x80\x8d\xf0\x9f\x91\xa6'
            u = b.decode("utf-8") * 1000
            global s
            count = 0
            while u:
                u = u[1:] # ID: index
                count += 1
            return count
        """, [1000])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('index', '''
            i51 = int_eq(1, i38)
            guard_false(i51, descr=...)
            i52 = strlen(p47)
            i53 = int_eq(i38, i52)
            guard_false(i53, descr=...)
            i56 = call_i(ConstClass(next_codepoint_pos_dont_look_inside), p47, 0, descr=...)
            i57 = int_sub(i52, i56)
            i59 = int_sub(i38, 1)
        ''')
