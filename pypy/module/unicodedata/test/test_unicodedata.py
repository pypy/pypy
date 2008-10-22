from py.test import raises
from pypy.conftest import gettestobjspace

class AppTestUnicodeData:
    def setup_class(cls):
        import random, unicodedata
        seed = random.getrandbits(32)
        print "random seed: ", seed
        random.seed(seed)
        space = gettestobjspace(usemodules=('unicodedata',))
        cls.space = space
        charlist_w = []
        nocharlist_w = []
        while len(charlist_w) < 1000 or len(nocharlist_w) < 1000:
            chr = unichr(random.randrange(65536))
            try:
                w_tup = space.newtuple([
                    space.wrap(chr), 
                    space.wrap(unicodedata.name(chr))
                    ])
                charlist_w.append(w_tup)
            except ValueError:
                nocharlist_w.append(space.wrap(chr))
        cls.w_charlist = space.newlist(charlist_w)
        cls.w_nocharlist = space.newlist(nocharlist_w)

    def test_hangul_syllables(self):
        import unicodedata
        # Test all leading, vowel and trailing jamo
        # but not every combination of them.
        for code, name in ((0xAC00, 'HANGUL SYLLABLE GA'),
                           (0xAE69, 'HANGUL SYLLABLE GGAEG'),
                           (0xB0D2, 'HANGUL SYLLABLE NYAGG'),
                           (0xB33B, 'HANGUL SYLLABLE DYAEGS'),
                           (0xB5A4, 'HANGUL SYLLABLE DDEON'),
                           (0xB80D, 'HANGUL SYLLABLE RENJ'),
                           (0xBA76, 'HANGUL SYLLABLE MYEONH'),
                           (0xBCDF, 'HANGUL SYLLABLE BYED'),
                           (0xBF48, 'HANGUL SYLLABLE BBOL'),
                           (0xC1B1, 'HANGUL SYLLABLE SWALG'),
                           (0xC41A, 'HANGUL SYLLABLE SSWAELM'),
                           (0xC683, 'HANGUL SYLLABLE OELB'),
                           (0xC8EC, 'HANGUL SYLLABLE JYOLS'),
                           (0xCB55, 'HANGUL SYLLABLE JJULT'),
                           (0xCDBE, 'HANGUL SYLLABLE CWEOLP'),
                           (0xD027, 'HANGUL SYLLABLE KWELH'),
                           (0xD290, 'HANGUL SYLLABLE TWIM'),
                           (0xD4F9, 'HANGUL SYLLABLE PYUB'),
                           (0xD762, 'HANGUL SYLLABLE HEUBS'),
                           (0xAE27, 'HANGUL SYLLABLE GYIS'),
                           (0xB090, 'HANGUL SYLLABLE GGISS'),
                           (0xB0AD, 'HANGUL SYLLABLE NANG'),
                           (0xB316, 'HANGUL SYLLABLE DAEJ'),
                           (0xB57F, 'HANGUL SYLLABLE DDYAC'),
                           (0xB7E8, 'HANGUL SYLLABLE RYAEK'),
                           (0xBA51, 'HANGUL SYLLABLE MEOT'),
                           (0xBCBA, 'HANGUL SYLLABLE BEP'),
                           (0xBF23, 'HANGUL SYLLABLE BBYEOH'),
                           (0xD7A3, 'HANGUL SYLLABLE HIH')):
            assert unicodedata.name(unichr(code)) == name
            assert unicodedata.lookup(name) == unichr(code)
        # Test outside the range
        raises(ValueError, unicodedata.name, unichr(0xAC00 - 1))
        raises(ValueError, unicodedata.name, unichr(0xD7A3 + 1))

    def test_cjk(self):
        import sys
        if sys.maxunicode < 0x10ffff:
            skip("requires a 'wide' python build.")
        import unicodedata
        cases = ((0x3400, 0x4DB5),
                 (0x4E00, 0x9FA5))
        if unicodedata.unidata_version >= "4.1":
            cases = ((0x3400, 0x4DB5),
                     (0x4E00, 0x9FBB),
                     (0x20000, 0x2A6D6))
        for first, last in cases:
            # Test at and inside the boundary
            for i in (first, first + 1, last - 1, last):
                charname = 'CJK UNIFIED IDEOGRAPH-%X'%i
                assert unicodedata.name(unichr(i)) == charname
                assert unicodedata.lookup(charname) == unichr(i)
            # Test outside the boundary
            for i in first - 1, last + 1:
                charname = 'CJK UNIFIED IDEOGRAPH-%X'%i
                try:
                    unicodedata.name(unichr(i))
                except ValueError:
                    pass
                raises(KeyError, unicodedata.lookup, charname)

    def test_random_charnames(self):
        import unicodedata
        for chr, name in self.charlist:
            assert unicodedata.name(chr) == name
            assert unicodedata.lookup(name) == chr

    def test_random_missing_chars(self):
        import unicodedata
        for chr in self.nocharlist:
            raises(ValueError, unicodedata.name, chr)
