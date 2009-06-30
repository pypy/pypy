import py
import sys, random
from pypy.rlib import runicode

class UnicodeTests(object):
    def typeequals(self, x, y):
        assert x == y
        assert type(x) is type(y)

    def getdecoder(self, encoding):
        return getattr(runicode, "str_decode_%s" % encoding.replace("-", "_"))

    def getencoder(self, encoding):
        return getattr(runicode,
                       "unicode_encode_%s" % encoding.replace("-", "_"))

    def checkdecode(self, s, encoding):
        decoder = self.getdecoder(encoding)
        if isinstance(s, str):
            trueresult = s.decode(encoding)
        else:
            trueresult = s
            s = s.encode(encoding)
        result, consumed = decoder(s, len(s), True)
        assert consumed == len(s)
        self.typeequals(trueresult, result)

    def checkencode(self, s, encoding):
        encoder = self.getencoder(encoding)
        if isinstance(s, unicode):
            trueresult = s.encode(encoding)
        else:
            trueresult = s
            s = s.decode(encoding)
        result = encoder(s, len(s), True)
        self.typeequals(trueresult, result)

    def checkencodeerror(self, s, encoding, start, stop):
        called = [False]
        def errorhandler(errors, enc, msg, t, startingpos,
                         endingpos):
            called[0] = True
            assert errors == "foo!"
            assert enc == encoding
            assert t is s
            assert start == startingpos
            assert stop == endingpos
            return "42424242", stop
        encoder = self.getencoder(encoding)
        result = encoder(s, len(s), "foo!", errorhandler)
        assert called[0]
        assert "42424242" in result

    def checkdecodeerror(self, s, encoding, start, stop, addstuff=True):
        called = [0]
        def errorhandler(errors, enc, msg, t, startingpos,
                         endingpos):
            called[0] += 1
            if called[0] == 1:
                assert errors == "foo!"
                assert enc == encoding
                assert t is s
                assert start == startingpos
                assert stop == endingpos
                return u"42424242", stop
            return "", endingpos
        decoder = self.getdecoder(encoding)
        if addstuff:
            s += "some rest in ascii"
        result, _ = decoder(s, len(s), "foo!", True, errorhandler)
        assert called[0] > 0
        assert "42424242" in result
        if addstuff:
            assert result.endswith(u"some rest in ascii")


class TestDecoding(UnicodeTests):
    
    # XXX test bom recognition in utf-16
    # XXX test proper error handling

    def test_all_ascii(self):
        for i in range(128):
            for encoding in "utf-8 latin-1 ascii".split():
                self.checkdecode(chr(i), encoding)

    def test_all_first_256(self):
        for i in range(256):
            for encoding in "utf-8 latin-1 utf-16 utf-16-be utf-16-le".split():
                self.checkdecode(unichr(i), encoding)

    def test_first_10000(self):
        for i in range(10000):
            for encoding in "utf-8 utf-16 utf-16-be utf-16-le".split():
                self.checkdecode(unichr(i), encoding)

    def test_random(self):
        for i in range(10000):
            v = random.randrange(sys.maxunicode)
            if 0xd800 <= v <= 0xdfff:
                continue
            uni = unichr(v)
            for encoding in "utf-8 utf-16 utf-16-be utf-16-le".split():
                self.checkdecode(uni, encoding)                

    def test_maxunicode(self):
        uni = unichr(sys.maxunicode)
        for encoding in "utf-8 utf-16 utf-16-be utf-16-le".split():
            self.checkdecode(uni, encoding)        

    def test_single_chars_utf8(self):
        for s in ["\xd7\x90", "\xd6\x96", "\xeb\x96\x95", "\xf0\x90\x91\x93"]:
            self.checkdecode(s, "utf-8")

    def test_utf8_errors(self):
        for s in [# unexpected end of data
                  "\xd7", "\xd6", "\xeb\x96", "\xf0\x90\x91"]:
            self.checkdecodeerror(s, "utf-8", 0, len(s), addstuff=False)
            
        for s in [# unexpected code byte
                  "\x81", "\xbf",
                  # invalid data 2 byte
                  "\xd7\x50", "\xd6\x06", "\xd6\xD6",
                  # invalid data 3 byte
                  "\xeb\x56\x95", "\xeb\x06\x95", "\xeb\xD6\x95",
                  "\xeb\x96\x55", "\xeb\x96\x05", "\xeb\x96\xD5",
                  # invalid data 4 byte
                  "\xf0\x50\x91\x93", "\xf0\x00\x91\x93", "\xf0\xd0\x91\x93", 
                  "\xf0\x90\x51\x93", "\xf0\x90\x01\x93", "\xf0\x90\xd1\x93", 
                  "\xf0\x90\x91\x53", "\xf0\x90\x91\x03", "\xf0\x90\x91\xd3", 
                  ]:
            self.checkdecodeerror(s, "utf-8", 0, len(s), addstuff=True)

    def test_ascii_error(self):
        self.checkdecodeerror("abc\xFF\xFF\xFFcde", "ascii", 3, 4)

    def test_utf16_errors(self):
        # trunkated BOM
        for s in ["\xff", "\xfe"]:
            self.checkdecodeerror(s, "utf-16", 0, len(s), addstuff=False)

        for s in [
                  # unexpected end of data ascii
                  "\xff\xfeF",
                  # unexpected end of data
                  '\xff\xfe\xc0\xdb\x00', '\xff\xfe\xc0\xdb', '\xff\xfe\xc0', 
                  ]:
            self.checkdecodeerror(s, "utf-16", 2, len(s), addstuff=False)
        for s in [
                  # illegal surrogate
                  "\xff\xfe\xff\xdb\xff\xff",
                  ]:
            self.checkdecodeerror(s, "utf-16", 2, 4, addstuff=False)

    def test_utf16_bugs(self):
        s = '\x80-\xe9\xdeL\xa3\x9b'
        py.test.raises(UnicodeDecodeError, runicode.str_decode_utf_16_le,
                       s, len(s), True)


class TestEncoding(UnicodeTests):
    def test_all_ascii(self):
        for i in range(128):
            for encoding in "utf-8 latin-1 ascii".split():
                self.checkencode(unichr(i), encoding)

    def test_all_first_256(self):
        for i in range(256):
            for encoding in "utf-8 latin-1 utf-16 utf-16-be utf-16-le".split():
                self.checkencode(unichr(i), encoding)

    def test_first_10000(self):
        for i in range(10000):
            for encoding in "utf-8 utf-16 utf-16-be utf-16-le".split():
                self.checkencode(unichr(i), encoding)

    def test_random(self):
        for i in range(10000):
            v = random.randrange(sys.maxunicode)
            if 0xd800 <= v <= 0xdfff:
                continue
            uni = unichr(v)
            for encoding in "utf-8 utf-16 utf-16-be utf-16-le".split():
                self.checkencode(uni, encoding)                

    def test_maxunicode(self):
        uni = unichr(sys.maxunicode)
        for encoding in "utf-8 utf-16 utf-16-be utf-16-le".split():
            self.checkencode(uni, encoding)        

    def test_single_chars_utf8(self):
        # check every number of bytes per char
        for s in ["\xd7\x90", "\xd6\x96", "\xeb\x96\x95", "\xf0\x90\x91\x93"]:
            self.checkencode(s, "utf-8")

    def test_utf8_surrogates(self):
        # check replacing of two surrogates by single char while encoding
        # make sure that the string itself is not marshalled
        u = u"\ud800" 
        for i in range(4):
            u += u"\udc00"
        self.checkencode(u, "utf-8")

    def test_ascii_error(self):
        self.checkencodeerror(u"abc\xFF\xFF\xFFcde", "ascii", 3, 6)

    def test_latin1_error(self):
        self.checkencodeerror(u"abc\uffff\uffff\uffffcde", "latin-1", 3, 6)

    def test_mbcs(self):
        if sys.platform != 'win32':
            py.test.skip("mbcs encoding is win32-specific")
        self.checkencode(u'encoding test', "mbcs")
        self.checkdecode('decoding test', "mbcs")
        # XXX test this on a non-western Windows installation
        self.checkencode(u"\N{GREEK CAPITAL LETTER PHI}", "mbcs") # a F
        self.checkencode(u"\N{GREEK CAPITAL LETTER PSI}", "mbcs") # a ?

class TestTranslation(object):
    def test_utf8(self):
        from pypy.rpython.test.test_llinterp import interpret
        def f(x):
            
            s1 = "".join(["\xd7\x90\xd6\x96\xeb\x96\x95\xf0\x90\x91\x93"] * x)
            u, consumed = runicode.str_decode_utf_8(s1, len(s1), True)
            s2 = runicode.unicode_encode_utf_8(u, len(u), True)
            return s1 == s2
        res = interpret(f, [2])
        assert res

    def test_surrogates(self):
        if runicode.MAXUNICODE < 65536:
            py.test.skip("Narrow unicode build")
        from pypy.rpython.test.test_llinterp import interpret
        def f(x):
            u = runicode.UNICHR(x)
            t = runicode.ORD(u)
            return t
            
        res = interpret(f, [0x10140])
        assert res == 0x10140
