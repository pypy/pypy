# encoding: utf-8
import random
import unicodedata

import py
import pytest

from rpython.rlib.unicodedata import (
    unicodedb_3_2_0, unicodedb_5_2_0,
    unicodedb_11_0_0, unicodedb_12_1_0, unicodedb_13_0_0)


class TestUnicodeData(object):
    def test_all_charnames_2bytes(self):
        if unicodedata.unidata_version != '5.2.0':
            py.test.skip('Needs python with unicode 5.2.0 database.')

        for i in range(65536):
            chr = unichr(i)
            try:
                name = unicodedata.name(chr)
            except ValueError:
                py.test.raises(KeyError, unicodedb_5_2_0.name, ord(chr))
            else:
                assert unicodedb_5_2_0.name(ord(chr)) == name
                assert unicodedb_5_2_0.lookup(name) == ord(chr)

    def test_isprintable(self):
        assert unicodedb_5_2_0.isprintable(ord(' '))
        assert unicodedb_5_2_0.isprintable(ord('a'))
        assert not unicodedb_5_2_0.isprintable(127)
        assert unicodedb_5_2_0.isprintable(0x00010346)  # GOTHIC LETTER FAIHU
        assert unicodedb_5_2_0.isprintable(0xfffd)  # REPLACEMENT CHARACTER
        assert unicodedb_5_2_0.isprintable(0xfffd)  # REPLACEMENT CHARACTER
        assert not unicodedb_5_2_0.isprintable(0xd800)  # SURROGATE
        assert not unicodedb_5_2_0.isprintable(0xE0020)  # TAG SPACE

    def test_identifier(self):
        assert unicodedb_5_2_0.isxidstart(ord('A'))
        assert not unicodedb_5_2_0.isxidstart(ord('_'))
        assert not unicodedb_5_2_0.isxidstart(ord('0'))
        assert not unicodedb_5_2_0.isxidstart(ord('('))
        assert unicodedb_5_2_0.isxidcontinue(ord('A'))
        assert unicodedb_5_2_0.isxidcontinue(ord('_'))
        assert unicodedb_5_2_0.isxidcontinue(ord('0'))
        assert not unicodedb_5_2_0.isxidcontinue(ord('('))
        oc = ord(u'日')
        assert unicodedb_5_2_0.isxidstart(oc)

    def test_compare_functions(self):
        def getX(fun, code):
            try:
                return getattr(unicodedb_5_2_0, fun)(code)
            except KeyError:
                return -1

        for code in range(0x10000):
            char = unichr(code)
            assert unicodedata.digit(char, -1) == getX('digit', code)
            assert unicodedata.numeric(char, -1) == getX('numeric', code)
            assert unicodedata.decimal(char, -1) == getX('decimal', code)
            assert unicodedata.category(char) == unicodedb_5_2_0.category(code)
            assert unicodedata.bidirectional(char) == unicodedb_5_2_0.bidirectional(code)
            assert unicodedata.decomposition(char) == unicodedb_5_2_0.decomposition(code)
            assert unicodedata.mirrored(char) == unicodedb_5_2_0.mirrored(code)
            assert unicodedata.combining(char) == unicodedb_5_2_0.combining(code)
            # east_asian_width has a different default for unassigned
            # characters on cpython (unicode says it should be 'N', CPython
            # returns 'F')
            n1 = None
            try:
                n1 = unicodedata.name(char)
            except ValueError:
                pass
            else:
                assert unicodedata.east_asian_width(char) == unicodedb_5_2_0.east_asian_width(code)

    def test_compare_methods(self):
        for code in range(0x10000):
            char = unichr(code)
            assert char.isalnum() == unicodedb_5_2_0.isalnum(code)
            assert char.isalpha() == unicodedb_5_2_0.isalpha(code)
            assert char.isdecimal() == unicodedb_5_2_0.isdecimal(code)
            assert char.isdigit() == unicodedb_5_2_0.isdigit(code)
            assert char.islower() == unicodedb_5_2_0.islower(code)
            assert char.isnumeric() == unicodedb_5_2_0.isnumeric(code)
            assert char.isspace() == unicodedb_5_2_0.isspace(code), hex(code)
            assert char.istitle() == (unicodedb_5_2_0.isupper(code) or unicodedb_5_2_0.istitle(code)), code
            assert char.isupper() == unicodedb_5_2_0.isupper(code)

            assert char.lower() == unichr(unicodedb_5_2_0.tolower(code))
            assert char.upper() == unichr(unicodedb_5_2_0.toupper(code))
            assert char.title() == unichr(unicodedb_5_2_0.totitle(code)), hex(code)

    def test_hangul_difference_520(self):
        assert unicodedb_5_2_0.name(40874) == 'CJK UNIFIED IDEOGRAPH-9FAA'

    def test_differences(self):
        assert unicodedb_5_2_0.name(9187) == 'BENZENE RING WITH CIRCLE'
        assert unicodedb_5_2_0.lookup('BENZENE RING WITH CIRCLE') == 9187
        py.test.raises(KeyError, unicodedb_3_2_0.lookup, 'BENZENE RING WITH CIRCLE')
        py.test.raises(KeyError, unicodedb_3_2_0.name, 9187)

    def test_casefolding(self):
        assert unicodedb_5_2_0.casefold_lookup(42592) == [42592]
        # 1010 has been remove between 3.2.0 and 5.2.0
        assert unicodedb_3_2_0.casefold_lookup(1010) == [963]
        assert unicodedb_5_2_0.casefold_lookup(1010) == [1010]
        # 7838 has been added in 5.2.0
        assert unicodedb_3_2_0.casefold_lookup(7838) == [7838]
        assert unicodedb_5_2_0.casefold_lookup(7838) == [115, 115]
        # Only lookup who cannot be resolved by `lower` are stored in database
        assert unicodedb_3_2_0.casefold_lookup(ord('E')) == [ord('e')]

    def test_canon_decomposition(self):
        assert unicodedb_3_2_0.compat_decomposition(296) == [73, 771]
        assert unicodedb_3_2_0.canon_decomposition(296) == [73, 771]
        assert unicodedb_3_2_0.compat_decomposition(32) == []
        assert unicodedb_3_2_0.canon_decomposition(32) == []

    def test_composition(self):
        # e + circumflex
        assert unicodedb_3_2_0.composition(ord('e'), 770) == 0xea
        with pytest.raises(KeyError):
            unicodedb_3_2_0.composition(ord('e'), ord('e'))

    def test_alias(self):
        with pytest.raises(KeyError):
            unicodedb_5_2_0.lookup("LATIN SMALL LETTER GHA")
        unicodedb_5_2_0.lookup("LATIN SMALL LETTER OI")
        assert unicodedb_5_2_0.name(0x01a3) == "LATIN SMALL LETTER OI"
        assert unicodedb_5_2_0.lookup_with_alias("LATIN SMALL LETTER GHA") == 0x01a3

class TestUnicodeData1100(object):
    def test_some_additions(self):
        additions = {
            ord(u"\u20B9"): 'INDIAN RUPEE SIGN',
            # u'\U0001F37A'
            127866: 'BEER MUG',
            # u'\U0001F37B'
            127867: 'CLINKING BEER MUGS',
            # u"\U0001F0AD"
            127149: 'PLAYING CARD QUEEN OF SPADES',
            # u"\U0002B740"
            177984: "CJK UNIFIED IDEOGRAPH-2B740",
            }
        for un, name in additions.iteritems():
            assert unicodedb_11_0_0.name(un) == name
            assert unicodedb_11_0_0.isprintable(un)

    def test_special_casing(self):
        assert unicodedb_11_0_0.tolower_full(ord('A')) == [ord('a')]
        # The German es-zed is special--the normal mapping is to SS.
        assert unicodedb_11_0_0.tolower_full(ord(u'\xdf')) == [0xdf]
        assert unicodedb_11_0_0.toupper_full(ord(u'\xdf')) == map(ord, 'SS')
        assert unicodedb_11_0_0.totitle_full(ord(u'\xdf')) == map(ord, 'Ss')

    def test_islower(self):
        assert unicodedb_11_0_0.islower(0x2177)

    def test_changed_in_version_8(self):
        assert unicodedb_5_2_0.toupper_full(0x025C) == [0x025C]
        assert unicodedb_11_0_0.toupper_full(0x025C) == [0xA7AB]

    def test_casefold(self):
        # when there is no special casefolding rule,
        # tolower_full() is returned instead
        assert unicodedb_11_0_0.casefold_lookup(0x1000) == unicodedb_11_0_0.tolower_full(0x1000)
        assert unicodedb_11_0_0.casefold_lookup(0x0061) == unicodedb_11_0_0.tolower_full(0x0061)
        assert unicodedb_11_0_0.casefold_lookup(0x0041) == unicodedb_11_0_0.tolower_full(0x0041)
        # a case where casefold() != lower()
        assert unicodedb_11_0_0.casefold_lookup(0x00DF) == [ord('s'), ord('s')]
        # returns the argument itself, and not None, in rare cases
        # where tolower_full() would return something different
        assert unicodedb_11_0_0.casefold_lookup(0x13A0) == [0x13A0]

        assert unicodedb_11_0_0.casefold_lookup(223) == [115, 115]
        assert unicodedb_11_0_0.casefold_lookup(976) == [946]

    def test_changed_in_version_11(self):
        unicodedb_11_0_0.name(0x1f970) == 'SMILING FACE WITH SMILING EYES AND THREE HEARTS'

@pytest.mark.parametrize('db', [
    unicodedb_5_2_0, unicodedb_11_0_0])
def test_turkish_i(db):
    assert db.tolower_full(0x0130) == [0x69, 0x307]

def test_era_reiwa():
    assert unicodedb_12_1_0.name(0x32ff) == 'SQUARE ERA NAME REIWA'

def test_unicode13():
    assert unicodedb_13_0_0.name(0x1fa97) == 'ACCORDION'
    assert unicodedb_13_0_0.name(0xd04) == 'MALAYALAM LETTER VEDIC ANUSVARA'

def test_unicode13_composition():
    # some random checks to see that stuff didn't completely break
    s = """
65 777 7842
65 772 256
69 803 7864
69 785 518
73 775 304
73 774 300
73 816 7724
75 807 310
76 769 313
79 795 416
79 772 332
79 770 212
79 779 336
85 770 219
85 771 360
89 776 376
97 778 229
97 803 7841
105 816 7725
105 776 239
110 769 324
111 808 491
117 769 250
119 776 7813
212 777 7892
416 769 7898
491 772 493
913 788 7945
953 776 970
1069 776 1260
1140 783 1142
1610 1620 1574
6929 6965 6930
7945 837 8073
8805 824 8817
8827 824 8833
69938 69927 69935"""
    l = []
    for line in s.strip().splitlines():
        a, b, x = line.split()
        l.append((int(a), int(b), int(x)))

    for a, b, x in l:
        assert unicodedb_13_0_0.composition(a, b) == x


def test_named_sequence():
    with pytest.raises(KeyError):
        unicodedb_13_0_0.lookup("KEYCAP DIGIT FIVE", with_named_sequence=False)
    assert unicodedb_13_0_0.lookup("KEYCAP DIGIT FIVE", with_named_sequence=True)
    code = unicodedb_13_0_0.lookup("KEYCAP DIGIT FIVE", with_named_sequence=True)
    assert unicodedb_13_0_0.lookup_named_sequence(code) == b'5\xef\xb8\x8f\xe2\x83\xa3'
    assert unicodedb_13_0_0.lookup_named_sequence_length(code) == 3

def test_cjk_13_missing_range_bug():
    assert unicodedb_13_0_0.name(0x30000) == 'CJK UNIFIED IDEOGRAPH-30000'
    assert unicodedb_13_0_0.name(0x3134a) == 'CJK UNIFIED IDEOGRAPH-3134a'
    assert unicodedb_13_0_0.name(0x3104f) == 'CJK UNIFIED IDEOGRAPH-3134a'

