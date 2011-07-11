from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

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

        log = self.run(main, [300])
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i14 = int_lt(i6, i9)
            guard_true(i14, descr=...)
            guard_not_invalidated(descr=...)
            i15 = int_mod(i6, i10)
            i17 = int_rshift(i15, 63)
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
            p30 = call(ConstClass(ll_str2unicode__rpy_stringPtr), p27, descr=<GcPtrCallDescr>)
            guard_no_exception(descr=...)
            i32 = call(ConstClass(_ll_2_str_eq_checknull_char__rpy_unicodePtr_UniChar), p30, i25, descr=<SignedCallDescr>)
            guard_true(i32, descr=...)
            i34 = int_add(i6, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i34, p7, p8, i9, i10, p11, i12, p13, descr=<Loop4>)
        """)

    def test_long(self):
        def main(n):
            import string
            i = 1
            while i < n:
                i += int(long(string.digits[i % len(string.digits)], 16))
            return i

        log = self.run(main, [1000])
        assert log.result == main(1000)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i11 = int_lt(i6, i7)
            guard_true(i11, descr=...)
            guard_not_invalidated(descr=...)
            i13 = int_eq(i6, -9223372036854775808)
            guard_false(i13, descr=...)
            i15 = int_mod(i6, i8)
            i17 = int_rshift(i15, 63)
            i18 = int_and(i8, i17)
            i19 = int_add(i15, i18)
            i21 = int_lt(i19, 0)
            guard_false(i21, descr=...)
            i22 = int_ge(i19, i8)
            guard_false(i22, descr=...)
            i23 = strgetitem(p10, i19)
            p25 = newstr(1)
            strsetitem(p25, 0, i23)
            p28 = call(ConstClass(strip_spaces), p25, descr=<GcPtrCallDescr>)
            guard_no_exception(descr=...)
            i29 = strlen(p28)
            i30 = int_is_true(i29)
            guard_true(i30, descr=...)
            i32 = int_sub(i29, 1)
            i33 = strgetitem(p28, i32)
            i35 = int_eq(i33, 108)
            guard_false(i35, descr=...)
            i37 = int_eq(i33, 76)
            guard_false(i37, descr=...)
            i39 = strgetitem(p28, 0)
            i41 = int_eq(i39, 45)
            guard_false(i41, descr=...)
            i43 = int_eq(i39, 43)
            guard_false(i43, descr=...)
            i43 = call(ConstClass(ll_startswith__rpy_stringPtr_rpy_stringPtr), p28, ConstPtr(ptr42), descr=<BoolCallDescr>)
            guard_false(i43, descr=...)
            i46 = call(ConstClass(ll_startswith__rpy_stringPtr_rpy_stringPtr), p28, ConstPtr(ptr45), descr=<BoolCallDescr>)
            guard_false(i46, descr=...)
            p51 = new_with_vtable(21136408)
            setfield_gc(p51, p28, descr=<GcPtrFieldDescr .*NumberStringParser.inst_literal .*>)
            setfield_gc(p51, ConstPtr(ptr51), descr=<GcPtrFieldDescr pypy.objspace.std.strutil.NumberStringParser.inst_fname .*>)
            setfield_gc(p51, 1, descr=<SignedFieldDescr .*NumberStringParser.inst_sign .*>)
            setfield_gc(p51, 16, descr=<SignedFieldDescr .*NumberStringParser.inst_base .*>)
            setfield_gc(p51, p28, descr=<GcPtrFieldDescr .*NumberStringParser.inst_s .*>)
            setfield_gc(p51, i29, descr=<SignedFieldDescr .*NumberStringParser.inst_n .*>)
            p55 = call(ConstClass(parse_digit_string), p51, descr=<GcPtrCallDescr>)
            guard_no_exception(descr=...)
            i57 = call(ConstClass(rbigint.toint), p55, descr=<SignedCallDescr>)
            guard_no_exception(descr=...)
            i58 = int_add_ovf(i6, i57)
            guard_no_overflow(descr=...)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i58, i7, i8, p9, p10, descr=<Loop4>)
        """)