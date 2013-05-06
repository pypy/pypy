# encoding: utf-8
import random
import unicodedata

import py

from rpython.rlib.unicodedata import (
    unicodedb_3_2_0, unicodedb_5_2_0, unicodedb_6_0_0)


class TestUnicodeData(object):
    def setup_class(cls):
        if unicodedata.unidata_version != '5.2.0':
            py.test.skip('Needs python with unicode 5.2.0 database.')

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
            py.test.raises(KeyError, unicodedb_5_2_0.name, ord(chr))

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


class TestUnicodeData600(object):

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
            assert unicodedb_6_0_0.name(un) == name
            assert unicodedb_6_0_0.isprintable(un)
