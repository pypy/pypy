import py
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

class TestArray(BaseTestPyPyC):

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
        log = self.run(main, [500])
        assert log.result == 500
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i5, i6)
            guard_true(i7, descr=...)
            i9 = int_add(i5, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, i9, i6, descr=<Loop0>)
        """)

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
            guard_not_invalidated(descr=...)
            i13 = int_lt(i7, i9)
            guard_true(i13, descr=...)
            i15 = getarrayitem_raw(i10, i7, descr=<.*ArrayNoLengthDescr>)
            i16 = int_add_ovf(i8, i15)
            guard_no_overflow(descr=...)
            i18 = int_add(i7, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, i18, i16, p8, i9, i10, descr=<Loop0>)
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
            guard_true(i13, descr=...)
            guard_not_invalidated(descr=...)
        # the bound check guard on img has been killed (thanks to the asserts)
            i14 = getarrayitem_raw(i10, i8, descr=<.*ArrayNoLengthDescr>)
            i15 = int_add_ovf(i9, i14)
            guard_no_overflow(descr=...)
            i17 = int_sub(i8, 640)
        # the bound check guard on intimg has been killed (thanks to the asserts)
            i18 = getarrayitem_raw(i11, i17, descr=<.*ArrayNoLengthDescr>)
            i19 = int_add_ovf(i18, i15)
            guard_no_overflow(descr=...)
        # on 64bit, there is a guard checking that i19 actually fits into 32bit
            ...
            setarrayitem_raw(i11, i8, _, descr=<.*ArrayNoLengthDescr>)
            i28 = int_add(i8, 1)
            --TICK--
            jump(p0, p1, p2, p3, p4, p5, p6, i28, i15, p9, i10, i11, descr=<Loop0>)
        """)

    def test_array_of_doubles(self):
        def main():
            from array import array
            img = array('d', [21.5]*1000)
            i = 0
            while i < 1000:
                img[i] += 20.5
                assert img[i] == 42.0
                i += 1
            return 123
        #
        log = self.run(main, [])
        assert log.result == 123
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i10 = int_lt(i6, 1000)
            guard_true(i10, descr=...)
            i11 = int_lt(i6, i7)
            guard_true(i11, descr=...)
            f13 = getarrayitem_raw(i8, i6, descr=<FloatArrayNoLengthDescr>)
            f15 = float_add(f13, 20.500000)
            setarrayitem_raw(i8, i6, f15, descr=<FloatArrayNoLengthDescr>)
            f16 = getarrayitem_raw(i8, i6, descr=<FloatArrayNoLengthDescr>)
            i18 = float_eq(f16, 42.000000)
            guard_true(i18, descr=...)
            i20 = int_add(i6, 1)
            --TICK--
            jump(..., descr=<Loop0>)
        """)

    def test_array_of_floats(self):
        def main():
            from array import array
            img = array('f', [21.5]*1000)
            i = 0
            while i < 1000:
                img[i] += 20.5
                assert img[i] == 42.0
                i += 1
            return 321
        #
        log = self.run(main, [])
        assert log.result == 321
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i10 = int_lt(i6, 1000)
            guard_true(i10, descr=...)
            i11 = int_lt(i6, i7)
            guard_true(i11, descr=...)
            i13 = getarrayitem_raw(i8, i6, descr=<UnsignedArrayNoLengthDescr>)
            f14 = cast_singlefloat_to_float(i13)
            f16 = float_add(f14, 20.500000)
            i17 = cast_float_to_singlefloat(f16)
            setarrayitem_raw(i8, i6,i17, descr=<UnsignedArrayNoLengthDescr>)
            i18 = getarrayitem_raw(i8, i6, descr=<UnsignedArrayNoLengthDescr>)
            f19 = cast_singlefloat_to_float(i18)
            i21 = float_eq(f19, 42.000000)
            guard_true(i21, descr=...)
            i23 = int_add(i6, 1)
            --TICK--
            jump(..., descr=<Loop0>)
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

        log = self.run(main, [])
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
        log = self.run(main, [])
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
            f20 = getarrayitem_raw(i8, i9, descr=...)
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
