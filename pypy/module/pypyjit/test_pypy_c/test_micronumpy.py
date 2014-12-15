from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC
from rpython.rlib.rawstorage import misaligned_is_fine


class TestMicroNumPy(BaseTestPyPyC):
    def test_reduce_logical_xor(self):
        def main():
            import _numpypy.multiarray as np
            import _numpypy.umath as um
            arr = np.array([1.0] * 1500)
            return um.logical_xor.reduce(arr)
        log = self.run(main, [])
        assert log.result is False
        assert len(log.loops) == 1
        loop = log._filter(log.loops[0])
        assert loop.match("""
            guard_class(p0, #, descr=...)
            p4 = getfield_gc_pure(p0, descr=<FieldP pypy.module.micronumpy.iterators.ArrayIter.inst_array \d+>)
            i5 = getfield_gc(p2, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset \d+>)
            p6 = getfield_gc_pure(p4, descr=<FieldP pypy.module.micronumpy.concrete.BaseConcreteArray.inst_dtype \d+>)
            p7 = getfield_gc_pure(p6, descr=<FieldP pypy.module.micronumpy.descriptor.W_Dtype.inst_itemtype \d+>)
            guard_class(p7, ConstClass(Float64), descr=...)
            i9 = getfield_gc_pure(p4, descr=<FieldU pypy.module.micronumpy.concrete.BaseConcreteArray.inst_storage \d+>)
            f10 = raw_load(i9, i5, descr=<ArrayF \d+>)
            i11 = getfield_gc_pure(p7, descr=<FieldU pypy.module.micronumpy.types.BaseType.inst_native \d+>)
            guard_true(i11, descr=...)
            guard_not_invalidated(descr=...)
            i12 = cast_float_to_int(f10)
            i14 = int_and(i12, 255)
            guard_true(i14, descr=...)
            i15 = getfield_gc_pure(p1, descr=<FieldU pypy.module.micronumpy.boxes.W_BoolBox.inst_value \d+>)
            i16 = int_is_true(i15)
            guard_false(i16, descr=...)
            i20 = getfield_gc(p2, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_index \d+>)
            i21 = getfield_gc_pure(p0, descr=<FieldU pypy.module.micronumpy.iterators.ArrayIter.inst_track_index \d+>)
            guard_true(i21, descr=...)
            i23 = int_add(i20, 1)
            p24 = getfield_gc_pure(p2, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst__indices \d+>)
            i25 = getfield_gc_pure(p0, descr=<FieldS pypy.module.micronumpy.iterators.ArrayIter.inst_contiguous \d+>)
            i26 = int_is_true(i25)
            guard_true(i26, descr=...)
            i27 = getfield_gc_pure(p6, descr=<FieldS pypy.module.micronumpy.descriptor.W_Dtype.inst_elsize \d+>)
            i28 = int_add(i5, i27)
            i29 = getfield_gc_pure(p0, descr=<FieldS pypy.module.micronumpy.iterators.ArrayIter.inst_size \d+>)
            i30 = int_ge(i23, i29)
            guard_false(i30, descr=...)
            p32 = new_with_vtable(#)
            {{{
            setfield_gc(p32, i23, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_index \d+>)
            setfield_gc(p32, p24, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst__indices \d+>)
            setfield_gc(p32, i28, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset \d+>)
            setfield_gc(p32, p0, descr=<FieldP pypy.module.micronumpy.iterators.IterState.inst_iterator \d+>)
            }}}
            jump(..., descr=...)
        """)

    def test_reduce_logical_and(self):
        def main():
            import _numpypy.multiarray as np
            import _numpypy.umath as um
            arr = np.array([1.0] * 1500)
            return um.logical_and.reduce(arr)
        log = self.run(main, [])
        assert log.result is True
        assert len(log.loops) == 1
        loop = log._filter(log.loops[0])
        assert loop.match("""
            f31 = raw_load(i9, i29, descr=<ArrayF 8>)
            guard_not_invalidated(descr=...)
            i32 = cast_float_to_int(f31)
            i33 = int_and(i32, 255)
            guard_true(i33, descr=...)
            i34 = getarrayitem_raw(#, #, descr=<ArrayU 1>)  # XXX what are these?
            guard_value(i34, #, descr=...)                  # XXX don't appear in
            i35 = getarrayitem_raw(#, #, descr=<ArrayU 1>)  # XXX equiv test_zjit
            i36 = int_add(i24, 1)
            i37 = int_add(i29, i28)
            i38 = int_ge(i36, i30)
            guard_false(i38, descr=...)
            guard_value(i35, #, descr=...)                  # XXX
            jump(..., descr=...)
        """)

    def test_array_getitem_basic(self):
        def main():
            import _numpypy.multiarray as np
            arr = np.zeros((300, 300))
            x = 150
            y = 0
            while y < 300:
                a = arr[x, y]
                y += 1
            return a
        log = self.run(main, [])
        assert log.result == 0
        loop, = log.loops_by_filename(self.filepath)
        if misaligned_is_fine:
            alignment_check = ""
        else:
            alignment_check = """
                i93 = int_and(i79, 7)
                i94 = int_is_zero(i93)
                guard_true(i94, descr=...)
            """
        assert loop.match("""
            i76 = int_lt(i71, 300)
            guard_true(i76, descr=...)
            i77 = int_ge(i71, i59)
            guard_false(i77, descr=...)
            i78 = int_mul(i71, i61)
            i79 = int_add(i55, i78)
            """ + alignment_check + """
            f80 = raw_load(i67, i79, descr=<ArrayF 8>)
            i81 = int_add(i71, 1)
            --TICK--
            jump(..., descr=...)
        """)

    def test_array_getitem_accumulate(self):
        """Check that operations/ufuncs on array items are jitted correctly"""
        def main():
            import _numpypy.multiarray as np
            arr = np.zeros((300, 300))
            a = 0.0
            x = 150
            y = 0
            while y < 300:
                a += arr[x, y]
                y += 1
            return a
        log = self.run(main, [])
        assert log.result == 0
        loop, = log.loops_by_filename(self.filepath)
        if misaligned_is_fine:
            alignment_check = ""
        else:
            alignment_check = """
                i97 = int_and(i84, 7)
                i98 = int_is_zero(i97)
                guard_true(i98, descr=...)
            """
        assert loop.match("""
            i81 = int_lt(i76, 300)
            guard_true(i81, descr=...)
            i82 = int_ge(i76, i62)
            guard_false(i82, descr=...)
            i83 = int_mul(i76, i64)
            i84 = int_add(i58, i83)
            """ + alignment_check + """
            f85 = raw_load(i70, i84, descr=<ArrayF 8>)
            guard_not_invalidated(descr=...)
            f86 = float_add(f74, f85)
            i87 = int_add(i76, 1)
            --TICK--
            jump(p0, p1, p3, p6, p7, p12, p14, f86, p18, i87, i62, p41, i58, p47, i40, i64, i70, descr=...)
        """)

    def test_array_flatiter_next(self):
        def main():
            import _numpypy.multiarray as np
            arr = np.zeros((1024, 16)) + 42
            ai = arr.flat
            i = 0
            while i < arr.size:
                a = next(ai)
                i += 1
            return a
        log = self.run(main, [])
        assert log.result == 42.0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i86 = int_lt(i79, i45)
            guard_true(i86, descr=...)
            guard_not_invalidated(descr=...)
            i88 = int_ge(i87, i59)
            guard_false(i88, descr=...)
            f90 = raw_load(i67, i89, descr=<ArrayF 8>)
            i91 = int_add(i87, 1)
            i93 = int_add(i89, i76)
            i94 = int_add(i79, 1)
            i95 = getfield_raw(#, descr=<FieldS pypysig_long_struct.c_value 0>)
            setfield_gc(p97, i91, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_index .+>)
            setfield_gc(p97, i93, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset .+>)
            i96 = int_lt(i95, 0)
            guard_false(i96, descr=...)
            jump(..., descr=...)
        """)

    def test_array_flatiter_getitem_single(self):
        def main():
            import _numpypy.multiarray as np
            arr = np.zeros((1024, 16)) + 42
            ai = arr.flat
            i = 0
            while i < arr.size:
                a = ai[i]
                i += 1
            return a
        log = self.run(main, [])
        assert log.result == 42.0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i125 = int_lt(i117, i44)
            guard_true(i125, descr=...)
            i126 = int_lt(i117, i50)
            guard_true(i126, descr=...)
            i128 = int_mul(i117, i59)
            i129 = int_add(i55, i128)
            f149 = raw_load(i100, i129, descr=<ArrayF 8>)
            i151 = int_add(i117, 1)
            setarrayitem_gc(p150, 1, 0, descr=<ArrayS .+>)
            setarrayitem_gc(p150, 0, 0, descr=<ArrayS .+>)
            setfield_gc(p156, i55, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset .+>)
            --TICK--
            jump(..., descr=...)
        """)

    def test_array_flatiter_setitem_single(self):
        def main():
            import _numpypy.multiarray as np
            arr = np.empty((1024, 16))
            ai = arr.flat
            i = 0
            while i < arr.size:
                ai[i] = 42.0
                i += 1
            return ai[-1]
        log = self.run(main, [])
        assert log.result == 42.0
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i128 = int_lt(i120, i42)
            guard_true(i128, descr=...)
            i129 = int_lt(i120, i48)
            guard_true(i129, descr=...)
            i131 = int_mul(i120, i57)
            i132 = int_add(i53, i131)
            guard_not_invalidated(descr=...)
            raw_store(i103, i132, 42.000000, descr=<ArrayF 8>)
            i153 = int_add(i120, 1)
            i154 = getfield_raw(#, descr=<FieldS pypysig_long_struct.c_value 0>)
            setarrayitem_gc(p152, 1, 0, descr=<ArrayS .+>)
            setarrayitem_gc(p152, 0, 0, descr=<ArrayS .+>)
            setfield_gc(p158, i53, descr=<FieldS pypy.module.micronumpy.iterators.IterState.inst_offset .+>)
            i157 = int_lt(i154, 0)
            guard_false(i157, descr=...)
            jump(..., descr=...)
        """)
