from rpython.jit.codewriter.liveness import compute_liveness, OFFSET_SIZE
from rpython.jit.codewriter.liveness import encode_offset, decode_offset
from rpython.jit.codewriter.liveness import encode_liveness, LivenessIterator
from rpython.jit.codewriter.format import unformat_assembler, assert_format

from hypothesis import strategies, given, example

class TestFlatten:

    def liveness_test(self, input, output):
        ssarepr = unformat_assembler(input)
        compute_liveness(ssarepr)
        assert_format(ssarepr, output)

    def test_simple_no_live(self):
        self.liveness_test("""
            -live-
            int_add %i0, $10 -> %i1
            -live-
        """, """
            -live- %i0
            int_add %i0, $10 -> %i1
            -live-
        """)

    def test_simple(self):
        self.liveness_test("""
            -live-
            int_add %i0, $10 -> %i1
            -live-
            int_add %i0, $3 -> %i2
            -live-
            int_mul %i1, %i2 -> %i3
            -live-
            int_add %i0, $6 -> %i4
            -live-
            int_mul %i3, %i4 -> %i5
            -live-
            int_return %i5
        """, """
            -live- %i0
            int_add %i0, $10 -> %i1
            -live- %i0, %i1
            int_add %i0, $3 -> %i2
            -live- %i0, %i1, %i2
            int_mul %i1, %i2 -> %i3
            -live- %i0, %i3
            int_add %i0, $6 -> %i4
            -live- %i3, %i4
            int_mul %i3, %i4 -> %i5
            -live- %i5
            int_return %i5
        """)

    def test_one_path(self):
        self.liveness_test("""
            int_add %i0, $5 -> %i2
            -live-
            int_is_true %i2 -> %i3
            goto_if_not %i3, L1
            int_copy %i0 -> %i4
            int_add %i4, $1 -> %i5
            -live-
            int_return %i5
            ---
            L1:
            int_copy %i1 -> %i6
            int_add %i6, $2 -> %i7
            -live-
            int_return %i7
        """, """
            int_add %i0, $5 -> %i2
            -live- %i0, %i1, %i2
            int_is_true %i2 -> %i3
            goto_if_not %i3, L1
            int_copy %i0 -> %i4
            int_add %i4, $1 -> %i5
            -live- %i5
            int_return %i5
            ---
            L1:
            int_copy %i1 -> %i6
            int_add %i6, $2 -> %i7
            -live- %i7
            int_return %i7
        """)

    def test_other_path(self):
        self.liveness_test("""
            int_add %i0, $5 -> %i2
            -live- %i2
            int_is_true %i2 -> %i3
            goto_if_not %i3, L1
            int_copy %i0 -> %i4
            int_copy %i1 -> %i5
            int_add %i4, %i5 -> %i6
            -live- %i6
            int_return %i6
            ---
            L1:
            int_copy %i0 -> %i7
            int_add %i7, $2 -> %i8
            -live- %i8
            int_return %i8
        """, """
            int_add %i0, $5 -> %i2
            -live- %i0, %i1, %i2
            int_is_true %i2 -> %i3
            goto_if_not %i3, L1
            int_copy %i0 -> %i4
            int_copy %i1 -> %i5
            int_add %i4, %i5 -> %i6
            -live- %i6
            int_return %i6
            ---
            L1:
            int_copy %i0 -> %i7
            int_add %i7, $2 -> %i8
            -live- %i8
            int_return %i8
        """)

    def test_no_path(self):
        self.liveness_test("""
            int_add %i0, %i1 -> %i2
            -live- %i2
            int_is_true %i2 -> %i3
            goto_if_not %i3, L1
            int_copy %i0 -> %i4
            int_add %i4, $5 -> %i5
            -live- %i5
            int_return %i5
            ---
            L1:
            int_copy %i0 -> %i6
            int_add %i6, $2 -> %i7
            -live- %i7
            int_return %i7
        """, """
            int_add %i0, %i1 -> %i2
            -live- %i0, %i2
            int_is_true %i2 -> %i3
            goto_if_not %i3, L1
            int_copy %i0 -> %i4
            int_add %i4, $5 -> %i5
            -live- %i5
            int_return %i5
            ---
            L1:
            int_copy %i0 -> %i6
            int_add %i6, $2 -> %i7
            -live- %i7
            int_return %i7
        """)

    def test_list_of_kind(self):
        self.liveness_test("""
            -live-
            foobar I[$25, %i0]
        """, """
            -live- %i0
            foobar I[$25, %i0]
        """)

    def test_switch(self):
        self.liveness_test("""
            goto_maybe L1
            -live-
            fooswitch <SwitchDictDescr 4:L2, 5:L3>
            ---
            L3:
            int_return %i7
            ---
            L1:
            int_return %i4
            ---
            L2:
            int_return %i3
        """, """
            goto_maybe L1
            -live- %i3, %i7
            fooswitch <SwitchDictDescr 4:L2, 5:L3>
            ---
            L3:
            int_return %i7
            ---
            L1:
            int_return %i4
            ---
            L2:
            int_return %i3
        """)

    def test_already_some(self):
        self.liveness_test("""
            foo %i0, %i1, %i2
            -live- %i0, $52, %i2, %i0
            bar %i3, %i4, %i5
        """, """
            foo %i0, %i1, %i2
            -live- %i0, %i2, %i3, %i4, %i5
            bar %i3, %i4, %i5
        """)

    def test_keepalive(self):
        self.liveness_test("""
            -live-
            build $1 -> %i6
            -live-
            foo %i0, %i1 -> %i2
            -live-
            bar %i3, %i2 -> %i5
            -live- %i6
        """, """
            -live- %i0, %i1, %i3
            build $1 -> %i6
            -live- %i0, %i1, %i3, %i6
            foo %i0, %i1 -> %i2
            -live- %i2, %i3, %i6
            bar %i3, %i2 -> %i5
            -live- %i6
        """)

    def test_live_with_label(self):
        self.liveness_test("""
            -live- L1
            foo %i0
            ---
            L1:
            bar %i1
        """, """
            -live- %i0, %i1, L1
            foo %i0
            ---
            L1:
            bar %i1
        """)

    def test_live_duplicate(self):
        self.liveness_test("""
            -live- L1
            -live- %i12
            foo %i0
            ---
            L1:
            bar %i1
        """, """
            -live- %i0, %i1, %i12, L1
            foo %i0
            ---
            L1:
            bar %i1
        """)
        self.liveness_test("""
            goto_if_not %i3, L1
            -live-
            L2:
            -live-
            L3:
            -live- %i19
            int_return %i0
            ---
            L1:
            int_add %i0, $1 -> %i0
            goto L2
        """, """
            goto_if_not %i3, L1
            L2:
            -live- %i0, %i19
            int_return %i0
            ---
            L1:
            int_add %i0, $1 -> %i0
            goto L2
        """)

class TestEncodeDecode(object):
    @given(strategies.integers(min_value=0, max_value=2**(8 * OFFSET_SIZE)-1), strategies.binary(), strategies.binary())
    def test_encode_decode_offset(self, x, prefix, postfix):
        l = []
        encode_offset(x, l)
        data = prefix + "".join(l) + postfix
        assert decode_offset(data, len(prefix)) == x

    def test_liveness_encoding(self):
        res = encode_liveness({})
        assert res == ''
        res = encode_liveness({'\x00'})
        assert res == '\x01'
        res = encode_liveness({'\x01'})
        assert res == '\x02'
        res = encode_liveness({'\x02'})
        assert res == '\x04'
        res = encode_liveness({'\x03'})
        assert res == '\x08'
        res = encode_liveness({'\x01', '\x02'})
        assert res == '\x06'
        res = encode_liveness({'\x08'})
        assert res == '\x00\x01'
        res = encode_liveness({'\x01', '\x09'})
        assert res == '\x02\x02'

    def test_liveness_iterator(self):
        liveness = '\x04\x01'
        l = list(LivenessIterator(0, 2, liveness))
        assert l == [2, 8]

    @example({0, 9})
    @given(strategies.sets(strategies.integers(min_value=0, max_value=255), min_size=1))
    def test_encode_decode_liveness(self, live):
        live_chars = [chr(i) for i in live]
        res = encode_liveness(live_chars)
        l = list(LivenessIterator(0, len(live), res))
        s = set(l)
        assert len(l) == len(s)
        assert s == live

    @given(strategies.sets(strategies.integers(min_value=0, max_value=255)),
           strategies.sets(strategies.integers(min_value=0, max_value=255)),
           strategies.sets(strategies.integers(min_value=0, max_value=255)))
    def test_encode_decode_liveness_3(self, live_i, live_r, live_f):
        live_i_chars = [chr(i) for i in live_i]
        live_r_chars = [chr(i) for i in live_r]
        live_f_chars = [chr(i) for i in live_f]
        all_liveness = encode_liveness(live_i_chars) + encode_liveness(live_r_chars) + encode_liveness(live_f_chars)
        offset = 0
        length_i = len(live_i)
        length_r = len(live_r)
        length_f = len(live_f)
        if length_i:
            it = LivenessIterator(offset, length_i, all_liveness)
            s = set(it)
            assert s == live_i
            offset = it.offset
        if length_r:
            it = LivenessIterator(offset, length_r, all_liveness)
            s = set(it)
            assert s == live_r
            offset = it.offset
        if length_f:
            it = LivenessIterator(offset, length_f, all_liveness)
            s = set(it)
            assert s == live_f
            offset = it.offset

