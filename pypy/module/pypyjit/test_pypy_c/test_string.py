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
            guard_true(i14, descr=<Guard42>)
            i15 = int_mod(i6, i10)
            i17 = int_rshift(i15, 63)
            i18 = int_and(i10, i17)
            i19 = int_add(i15, i18)
            i21 = int_lt(i19, 0)
            guard_false(i21, descr=<Guard43>)
            i22 = int_ge(i19, i10)
            guard_false(i22, descr=<Guard44>)
            i23 = strgetitem(p11, i19)
            i24 = int_ge(i19, i12)
            guard_false(i24, descr=<Guard45>)
            i25 = unicodegetitem(p13, i19)
            guard_not_invalidated(descr=<Guard46>)
            p27 = newstr(1)
            strsetitem(p27, 0, i23)
            p30 = call(ConstClass(ll_str2unicode__rpy_stringPtr), p27, descr=<GcPtrCallDescr>)
            guard_no_exception(descr=<Guard47>)
            i32 = call(ConstClass(_ll_2_str_eq_checknull_char__rpy_unicodePtr_UniChar), p30, i25, descr=<SignedCallDescr>)
            guard_true(i32, descr=<Guard48>)
            i34 = int_add(i6, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i34, p7, p8, i9, i10, p11, i12, p13, descr=<Loop4>)
        """)