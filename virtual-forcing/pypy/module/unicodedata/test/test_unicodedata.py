from py.test import raises, skip
from pypy.conftest import gettestobjspace

from pypy.module.unicodedata import unicodedb_4_1_0, unicodedb_3_2_0, unicodedb_5_0_0

class AppTestUnicodeData:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('unicodedata',))
        cls.space = space

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

    def test_bug_1704793(self): # from CPython
        import sys, unicodedata
        if sys.maxunicode == 65535:
            raises(KeyError, unicodedata.lookup, "GOTHIC LETTER FAIHU")

    def test_normalize(self):
        import unicodedata
        raises(TypeError, unicodedata.normalize, 'x')

class TestUnicodeData(object):
    def setup_class(cls):
        import random, unicodedata
        if unicodedata.unidata_version != '4.1.0':
            skip('Needs python with unicode 4.1.0 database.')

        seed = random.getrandbits(32)
        print "random seed: ", seed
        random.seed(seed)
        cls.charlist = charlist = []
        cls.nocharlist = nocharlist = []
        while len(charlist) < 1000 or len(nocharlist) < 1000:
            chr = unichr(random.randrange(65536))
            try:
                charlist.append((chr, unicodedata.name(chr)))
            except ValueError:
                nocharlist.append(chr)

    def test_random_charnames(self):
        for chr, name in self.charlist:
            assert unicodedb_4_1_0.name(ord(chr)) == name
            assert unicodedb_4_1_0.lookup(name) == ord(chr)

    def test_random_missing_chars(self):
        for chr in self.nocharlist:
            raises(KeyError, unicodedb_4_1_0.name, ord(chr))

    diff_numeric = set([0x3405, 0x3483, 0x382a, 0x3b4d, 0x4e00, 0x4e03,
                        0x4e07, 0x4e09, 0x4e5d, 0x4e8c, 0x4e94, 0x4e96,
                        0x4ebf, 0x4ec0, 0x4edf, 0x4ee8, 0x4f0d, 0x4f70,
                        0x5104, 0x5146, 0x5169, 0x516b, 0x516d, 0x5341,
                        0x5343, 0x5344, 0x5345, 0x534c, 0x53c1, 0x53c2,
                        0x53c3, 0x53c4, 0x56db, 0x58f1, 0x58f9, 0x5e7a,
                        0x5efe, 0x5eff, 0x5f0c, 0x5f0d, 0x5f0e, 0x5f10,
                        0x62fe, 0x634c, 0x67d2, 0x7396, 0x767e, 0x8086,
                        0x842c, 0x8cae, 0x8cb3, 0x8d30, 0x9646, 0x964c,
                        0x9678, 0x96f6])

    diff_title = set([0x01c5, 0x01c8, 0x01cb, 0x01f2])

    diff_isspace = set([0x180e, 0x200b])
    
    def test_compare_functions(self):
        import unicodedata # CPython implementation

        def getX(fun, code):
            if fun == 'numeric' and code in self.diff_numeric:
                return -1
            try:
                return getattr(unicodedb_4_1_0, fun)(code)
            except KeyError:
                return -1
        
        for code in range(0x10000):
            char = unichr(code)
            assert unicodedata.digit(char, -1) == getX('digit', code)
            assert unicodedata.numeric(char, -1) == getX('numeric', code)
            assert unicodedata.decimal(char, -1) == getX('decimal', code)
            assert unicodedata.category(char) == unicodedb_4_1_0.category(code)
            assert unicodedata.bidirectional(char) == unicodedb_4_1_0.bidirectional(code)
            assert unicodedata.decomposition(char) == unicodedb_4_1_0.decomposition(code)
            assert unicodedata.mirrored(char) == unicodedb_4_1_0.mirrored(code)
            assert unicodedata.combining(char) == unicodedb_4_1_0.combining(code)

    def test_compare_methods(self):
        for code in range(0x10000):
            char = unichr(code)
            assert char.isalnum() == unicodedb_4_1_0.isalnum(code)
            assert char.isalpha() == unicodedb_4_1_0.isalpha(code)
            assert char.isdecimal() == unicodedb_4_1_0.isdecimal(code)
            assert char.isdigit() == unicodedb_4_1_0.isdigit(code)
            assert char.islower() == unicodedb_4_1_0.islower(code)
            assert (code in self.diff_numeric or char.isnumeric()) == unicodedb_4_1_0.isnumeric(code)
            assert code in self.diff_isspace or char.isspace() == unicodedb_4_1_0.isspace(code), hex(code)
            assert char.istitle() == (unicodedb_4_1_0.isupper(code) or unicodedb_4_1_0.istitle(code)), code
            assert char.isupper() == unicodedb_4_1_0.isupper(code)

            assert char.lower() == unichr(unicodedb_4_1_0.tolower(code))
            assert char.upper() == unichr(unicodedb_4_1_0.toupper(code))
            assert code in self.diff_title or char.title() == unichr(unicodedb_4_1_0.totitle(code)), hex(code)

    def test_hangul_difference_410(self):
        assert unicodedb_4_1_0.name(40874) == 'CJK UNIFIED IDEOGRAPH-9FAA'

    def test_differences(self):
        assert unicodedb_5_0_0.name(9187) == 'BENZENE RING WITH CIRCLE'
        assert unicodedb_5_0_0.lookup('BENZENE RING WITH CIRCLE') == 9187
        raises(KeyError, unicodedb_3_2_0.lookup, 'BENZENE RING WITH CIRCLE')
        raises(KeyError, unicodedb_4_1_0.lookup, 'BENZENE RING WITH CIRCLE')
        raises(KeyError, unicodedb_3_2_0.name, 9187)
        raises(KeyError, unicodedb_4_1_0.name, 9187)


