from py.test import raises, skip
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin
from pypy.conftest import gettestobjspace

from pypy.module.unicodedata import unicodedb_3_2_0, unicodedb_5_2_0

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
                char = ('\\U%08X' % i).decode('unicode-escape')
                assert unicodedata.name(char) == charname
                assert unicodedata.lookup(charname) == char
            # Test outside the boundary
            for i in first - 1, last + 1:
                charname = 'CJK UNIFIED IDEOGRAPH-%X'%i
                char = ('\\U%08X' % i).decode('unicode-escape')
                try:
                    unicodedata.name(char)
                except ValueError, e:
                    assert e.message == 'no such name'
                raises(KeyError, unicodedata.lookup, charname)

    def test_bug_1704793(self): # from CPython
        import unicodedata
        assert unicodedata.lookup("GOTHIC LETTER FAIHU") == u'\U00010346'

    def test_normalize(self):
        import unicodedata
        raises(TypeError, unicodedata.normalize, 'x')

    def test_normalize_wide(self):
        import sys, unicodedata
        if sys.maxunicode < 0x10ffff:
            skip("requires a 'wide' python build.")
        assert unicodedata.normalize('NFC', u'\U000110a5\U000110ba') == u'\U000110ab'

    def test_linebreaks(self):
        linebreaks = (0x0a, 0x0b, 0x0c, 0x0d, 0x85,
                      0x1c, 0x1d, 0x1e, 0x2028, 0x2029)
        for i in linebreaks:
            for j in range(-2, 3):
                lines = (unichr(i + j) + u'A').splitlines()
                if i + j in linebreaks:
                    assert len(lines) == 2
                else:
                    assert len(lines) == 1

    def test_mirrored(self):
        import unicodedata
        # For no reason, unicodedata.mirrored() returns an int, not a bool
        assert repr(unicodedata.mirrored(u' ')) == '0'

class TestUnicodeData(object):
    def setup_class(cls):
        import random, unicodedata
        if unicodedata.unidata_version != '5.2.0':
            skip('Needs python with unicode 5.2.0 database.')

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
            assert unicodedb_5_2_0.name(ord(chr)) == name
            assert unicodedb_5_2_0.lookup(name) == ord(chr)

    def test_random_missing_chars(self):
        for chr in self.nocharlist:
            raises(KeyError, unicodedb_5_2_0.name, ord(chr))

    def test_compare_functions(self):
        import unicodedata # CPython implementation

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
        raises(KeyError, unicodedb_3_2_0.lookup, 'BENZENE RING WITH CIRCLE')
        raises(KeyError, unicodedb_3_2_0.name, 9187)

class TestTranslated(BaseRtypingTest, LLRtypeMixin):

    def test_translated(self):
        def f(n):
            if n == 0:
                return -1
            else:
                u = unicodedb_5_2_0.lookup("GOTHIC LETTER FAIHU")
                return u
        res = self.interpret(f, [1])
        print hex(res)
        assert res == f(1)

    def test_code_to_unichr(self):
        from pypy.module.unicodedata.interp_ucd import code_to_unichr
        def f(c):
            return code_to_unichr(c) + u''
        res = self.ll_to_unicode(self.interpret(f, [0x10346]))
        assert res == u'\U00010346'



