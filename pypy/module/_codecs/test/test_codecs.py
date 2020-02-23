import sys

class AppTestCodecs:
    spaceconfig = {
        "usemodules": ['unicodedata', 'struct', 'binascii'],
    }

    def test_register_noncallable(self):
        import _codecs
        raises(TypeError, _codecs.register, 1)

    def test_bigU_codecs(self):
        u = u'\U00010001\U00020002\U00030003\U00040004\U00050005'
        for encoding in ('utf-8', 'utf-16', 'utf-16-le', 'utf-16-be',
                         'utf-32', 'utf-32-le', 'utf-32-be',
                         'raw_unicode_escape',
                         'unicode_escape', 'unicode_internal'):
            assert unicode(u.encode(encoding),encoding) == u

    def test_ucs4(self):
        x = u'\U00100000'
        y = x.encode("raw-unicode-escape").decode("raw-unicode-escape")
        assert x == y

    def test_named_unicode(self):
        assert unicode('\\N{SPACE}','unicode-escape') == u" "
        raises( UnicodeDecodeError, unicode,'\\N{SPACE','unicode-escape')
        raises( UnicodeDecodeError, unicode,'\\NSPACE}','unicode-escape')
        raises( UnicodeDecodeError, unicode,'\\NSPACE','unicode-escape')
        raises( UnicodeDecodeError, unicode,'\\N','unicode-escape')
        assert  unicode('\\N{SPACE}\\N{SPACE}','unicode-escape') == u"  "
        assert  unicode('\\N{SPACE}a\\N{SPACE}','unicode-escape') == u" a "
        assert "\\N{foo}xx".decode("unicode-escape", "ignore") == u"xx"
        assert 1 <= len(u"\N{CJK UNIFIED IDEOGRAPH-20000}") <= 2

    def test_literals(self):
        raises(SyntaxError, eval, 'u\'\\Uffffffff\'')

    def test_insecure_pickle(self):
        import pickle
        insecure = ["abc", "2 + 2", # not quoted
                    #"'abc' + 'def'", # not a single quoted string
                    "'abc", # quote is not closed
                    "'abc\"", # open quote and close quote don't match
                    "'abc'   ?", # junk after close quote
                    "'\\'", # trailing backslash
                    # some tests of the quoting rules
                    #"'abc\"\''",
                    #"'\\\\a\'\'\'\\\'\\\\\''",
                    ]
        for s in insecure:
            buf = "S" + s + "\012p0\012."
            raises (ValueError, pickle.loads, buf)

    def test_unicodedecodeerror(self):
        assert str(UnicodeDecodeError(
            "ascii", "g\xfcrk", 1, 2, "ouch")) == "'ascii' codec can't decode byte 0xfc in position 1: ouch"

        assert str(UnicodeDecodeError(
            "ascii", "g\xfcrk", 1, 3, "ouch")) == "'ascii' codec can't decode bytes in position 1-2: ouch"

    def test_unicodetranslateerror(self):
        import sys
        assert str(UnicodeTranslateError(
            u"g\xfcrk", 1, 2, "ouch"))== "can't translate character u'\\xfc' in position 1: ouch"

        assert str(UnicodeTranslateError(
            u"g\u0100rk", 1, 2, "ouch"))== "can't translate character u'\\u0100' in position 1: ouch"

        assert str(UnicodeTranslateError(
            u"g\uffffrk", 1, 2, "ouch"))== "can't translate character u'\\uffff' in position 1: ouch"

        if sys.maxunicode > 0xffff and len(unichr(0x10000)) == 1:
            assert str(UnicodeTranslateError(
                u"g\U00010000rk", 1, 2, "ouch"))== "can't translate character u'\\U00010000' in position 1: ouch"

        assert str(UnicodeTranslateError(
            u"g\xfcrk", 1, 3, "ouch"))=="can't translate characters in position 1-2: ouch"

    def test_unicodeencodeerror(self):
        import sys
        assert str(UnicodeEncodeError(
            "ascii", u"g\xfcrk", 1, 2, "ouch"))=="'ascii' codec can't encode character u'\\xfc' in position 1: ouch"

        assert str(UnicodeEncodeError(
            "ascii", u"g\xfcrk", 1, 4, "ouch"))== "'ascii' codec can't encode characters in position 1-3: ouch"

        assert str(UnicodeEncodeError(
            "ascii", u"\xfcx", 0, 1, "ouch"))=="'ascii' codec can't encode character u'\\xfc' in position 0: ouch"

        assert str(UnicodeEncodeError(
            "ascii", u"\u0100x", 0, 1, "ouch"))=="'ascii' codec can't encode character u'\\u0100' in position 0: ouch"

        assert str(UnicodeEncodeError(
            "ascii", u"\uffffx", 0, 1, "ouch"))=="'ascii' codec can't encode character u'\\uffff' in position 0: ouch"
        if sys.maxunicode > 0xffff and len(unichr(0x10000)) == 1:
            assert str(UnicodeEncodeError(
                "ascii", u"\U00010000x", 0, 1, "ouch")) =="'ascii' codec can't encode character u'\\U00010000' in position 0: ouch"

    def test_indexerror(self):
        test =   "\\"     # trailing backslash
        raises (ValueError, test.decode,'string-escape')

    def test_charmap_decode(self):
        from _codecs import charmap_decode
        import sys
        assert charmap_decode('', 'strict', 'blablabla') == ('', 0)
        assert charmap_decode('xxx') == ('xxx', 3)
        assert charmap_decode('xxx', 'strict', {ord('x'): u'XX'}) == ('XXXXXX', 3)
        map = tuple([unichr(i) for i in range(256)])
        assert charmap_decode('xxx\xff', 'strict', map) == (u'xxx\xff', 4)

        exc = raises(TypeError, charmap_decode, '\xff', "strict",  {0xff: 'a'})
        assert str(exc.value) == "character mapping must return integer, None or unicode"
        raises(TypeError, charmap_decode, '\xff', "strict",  {0xff: 0x110000})
        assert (charmap_decode("\x00\x01\x02", "strict",
                               {0: 0x10FFFF, 1: ord('b'), 2: ord('c')}) ==
                (u"\U0010FFFFbc", 3))
        assert (charmap_decode("\x00\x01\x02", "strict",
                               {0: u'\U0010FFFF', 1: u'b', 2: u'c'}) ==
                (u"\U0010FFFFbc", 3))
        assert charmap_decode('\xff', "strict", {0xff: 0xd800}) == (u'\ud800', 1)

    def test_escape_decode(self):
        from _codecs import unicode_escape_decode as decode
        assert decode('\\\x80') == (u'\\\x80', 2)

    def test_escape_decode_errors(self):
        from _codecs import escape_decode as decode
        raises(ValueError, decode, br"\x")
        raises(ValueError, decode, br"[\x]")
        assert decode(br"[\x]\x", "ignore") == (b"[]", 6)
        assert decode(br"[\x]\x", "replace") == (b"[?]?", 6)
        raises(ValueError, decode, br"\x0")
        raises(ValueError, decode, br"[\x0]")
        assert decode(br"[\x0]\x0", "ignore") == (b"[]", 8)
        assert decode(br"[\x0]\x0", "replace") == (b"[?]?", 8)

    def test_unicode_escape(self):
        from _codecs import unicode_escape_encode, unicode_escape_decode
        assert unicode_escape_encode(u'abc') == (u'abc'.encode('unicode_escape'), 3)
        assert unicode_escape_decode('abc') == (u'abc'.decode('unicode_escape'), 3)
        assert unicode_escape_decode('\\x61\\x62\\x63') == (u'abc', 12)

    def test_unicode_replace(self):
        # CPython #8271: during the decoding of an invalid UTF-8 byte sequence,
        # only the start byte and the continuation byte(s) are now considered
        # invalid, instead of the number of bytes specified by the start byte.
        # See http://www.unicode.org/versions/Unicode5.2.0/ch03.pdf (page 42,
        # table 3-8, Row 2) for more information about the algorithm used.
        FFFD = u'\ufffd'
        sequences = [
            # invalid start bytes
            (b'\x80', FFFD), # continuation byte
            (b'\x80\x80', FFFD*2), # 2 continuation bytes
            (b'\xc0', FFFD),
            (b'\xc0\xc0', FFFD*2),
            (b'\xc1', FFFD),
            (b'\xc1\xc0', FFFD*2),
            (b'\xc0\xc1', FFFD*2),
            # with start byte of a 2-byte sequence
            (b'\xc2', FFFD), # only the start byte
            (b'\xc2\xc2', FFFD*2), # 2 start bytes
            (b'\xc2\xc2\xc2', FFFD*3), # 3 start bytes
            (b'\xc2\x41', FFFD+'A'), # invalid continuation byte
            # with start byte of a 3-byte sequence
            (b'\xe1', FFFD), # only the start byte
            (b'\xe1\xe1', FFFD*2), # 2 start bytes
            (b'\xe1\xe1\xe1', FFFD*3), # 3 start bytes
            (b'\xe1\xe1\xe1\xe1', FFFD*4), # 4 start bytes
            (b'\xe1\x80', FFFD), # only 1 continuation byte
            (b'\xe1\x41', FFFD+'A'), # invalid continuation byte
            (b'\xe1\x41\x80', FFFD+'A'+FFFD), # invalid cb followed by valid cb
            (b'\xe1\x41\x41', FFFD+'AA'), # 2 invalid continuation bytes
            (b'\xe1\x80\x41', FFFD+'A'), # only 1 valid continuation byte
            (b'\xe1\x80\xe1\x41', FFFD*2+'A'), # 1 valid and the other invalid
            (b'\xe1\x41\xe1\x80', FFFD+'A'+FFFD), # 1 invalid and the other valid
            # with start byte of a 4-byte sequence
            (b'\xf1', FFFD), # only the start byte
            (b'\xf1\xf1', FFFD*2), # 2 start bytes
            (b'\xf1\xf1\xf1', FFFD*3), # 3 start bytes
            (b'\xf1\xf1\xf1\xf1', FFFD*4), # 4 start bytes
            (b'\xf1\xf1\xf1\xf1\xf1', FFFD*5), # 5 start bytes
            (b'\xf1\x80', FFFD), # only 1 continuation bytes
            (b'\xf1\x80\x80', FFFD), # only 2 continuation bytes
            (b'\xf1\x80\x41', FFFD+'A'), # 1 valid cb and 1 invalid
            (b'\xf1\x80\x41\x41', FFFD+'AA'), # 1 valid cb and 1 invalid
            (b'\xf1\x80\x80\x41', FFFD+'A'), # 2 valid cb and 1 invalid
            (b'\xf1\x41\x80', FFFD+'A'+FFFD), # 1 invalid cv and 1 valid
            (b'\xf1\x41\x80\x80', FFFD+'A'+FFFD*2), # 1 invalid cb and 2 invalid
            (b'\xf1\x41\x80\x41', FFFD+'A'+FFFD+'A'), # 2 invalid cb and 1 invalid
            (b'\xf1\x41\x41\x80', FFFD+'AA'+FFFD), # 1 valid cb and 1 invalid
            (b'\xf1\x41\xf1\x80', FFFD+'A'+FFFD),
            (b'\xf1\x41\x80\xf1', FFFD+'A'+FFFD*2),
            (b'\xf1\xf1\x80\x41', FFFD*2+'A'),
            (b'\xf1\x41\xf1\xf1', FFFD+'A'+FFFD*2),
            # with invalid start byte of a 4-byte sequence (rfc2279)
            (b'\xf5', FFFD), # only the start byte
            (b'\xf5\xf5', FFFD*2), # 2 start bytes
            (b'\xf5\x80', FFFD*2), # only 1 continuation byte
            (b'\xf5\x80\x80', FFFD*3), # only 2 continuation byte
            (b'\xf5\x80\x80\x80', FFFD*4), # 3 continuation bytes
            (b'\xf5\x80\x41', FFFD*2+'A'), #  1 valid cb and 1 invalid
            (b'\xf5\x80\x41\xf5', FFFD*2+'A'+FFFD),
            (b'\xf5\x41\x80\x80\x41', FFFD+'A'+FFFD*2+'A'),
            # with invalid start byte of a 5-byte sequence (rfc2279)
            (b'\xf8', FFFD), # only the start byte
            (b'\xf8\xf8', FFFD*2), # 2 start bytes
            (b'\xf8\x80', FFFD*2), # only one continuation byte
            (b'\xf8\x80\x41', FFFD*2 + 'A'), # 1 valid cb and 1 invalid
            (b'\xf8\x80\x80\x80\x80', FFFD*5), # invalid 5 bytes seq with 5 bytes
            # with invalid start byte of a 6-byte sequence (rfc2279)
            (b'\xfc', FFFD), # only the start byte
            (b'\xfc\xfc', FFFD*2), # 2 start bytes
            (b'\xfc\x80\x80', FFFD*3), # only 2 continuation bytes
            (b'\xfc\x80\x80\x80\x80\x80', FFFD*6), # 6 continuation bytes
            # invalid start byte
            (b'\xfe', FFFD),
            (b'\xfe\x80\x80', FFFD*3),
            # other sequences
            (b'\xf1\x80\x41\x42\x43', u'\ufffd\x41\x42\x43'),
            (b'\xf1\x80\xff\x42\x43', u'\ufffd\ufffd\x42\x43'),
            (b'\xf1\x80\xc2\x81\x43', u'\ufffd\x81\x43'),
            (b'\x61\xF1\x80\x80\xE1\x80\xC2\x62\x80\x63\x80\xBF\x64',
             u'\x61\uFFFD\uFFFD\uFFFD\x62\uFFFD\x63\uFFFD\uFFFD\x64'),
        ]
        for n, (seq, res) in enumerate(sequences):
            raises(UnicodeDecodeError, seq.decode, 'utf-8', 'strict')
            uni = seq.decode('utf-8', 'replace')
            assert uni == res
            uni = (seq+b'b').decode('utf-8', 'replace')
            assert uni == res+'b'
            uni = seq.decode('utf-8', 'ignore')
            assert uni == res.replace(u'\uFFFD', '')


class AppTestPartialEvaluation:
    spaceconfig = dict(usemodules=['array',])
    if sys.platform == 'win32':
        spaceconfig['usemodules'].append('_winreg')

    def test_partial_utf8(self):
        import _codecs
        encoding = 'utf-8'
        check_partial = [
                u"\x00",
                u"\x00",
                u"\x00\xff",
                u"\x00\xff",
                u"\x00\xff\u07ff",
                u"\x00\xff\u07ff",
                u"\x00\xff\u07ff",
                u"\x00\xff\u07ff\u0800",
                u"\x00\xff\u07ff\u0800",
                u"\x00\xff\u07ff\u0800",
                u"\x00\xff\u07ff\u0800\uffff",
                u"\x00\xff\u07ff\u0800\uffff",
                u"\x00\xff\u07ff\u0800\uffff",
                u"\x00\xff\u07ff\u0800\uffff",
                u"\x00\xff\u07ff\u0800\uffff\U00010000",
            ]

        buffer = ''
        result = u""
        for (c, partialresult) in zip(u"\x00\xff\u07ff\u0800\uffff\U00010000".encode(encoding), check_partial):
            buffer += c
            res = _codecs.utf_8_decode(buffer,'strict',False)
            if res[1] >0 :
                buffer = ''
            result += res[0]
            assert result == partialresult

    def test_partial_utf16(self):
        import _codecs
        encoding = 'utf-16'
        check_partial = [
                    u"", # first byte of BOM read
                    u"", # second byte of BOM read => byteorder known
                    u"",
                    u"\x00",
                    u"\x00",
                    u"\x00\xff",
                    u"\x00\xff",
                    u"\x00\xff\u0100",
                    u"\x00\xff\u0100",
                    u"\x00\xff\u0100\uffff",
                    u"\x00\xff\u0100\uffff",
                    u"\x00\xff\u0100\uffff",
                    u"\x00\xff\u0100\uffff",
                    u"\x00\xff\u0100\uffff\U00010000",
                ]
        buffer = ''
        result = u""
        for (c, partialresult) in zip(u"\x00\xff\u0100\uffff\U00010000".encode(encoding), check_partial):
            buffer += c
            res = _codecs.utf_16_decode(buffer,'strict',False)
            if res[1] >0 :
                buffer = ''
            result += res[0]
            assert result == partialresult

    def test_bug1098990_a(self):
        import codecs, StringIO
        self.encoding = 'utf-8'
        s1 = u"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\r\n"
        s2 = u"offending line: ladfj askldfj klasdj fskla dfzaskdj fasklfj laskd fjasklfzzzzaa%whereisthis!!!\r\n"
        s3 = u"next line.\r\n"

        s = (s1+s2+s3).encode(self.encoding)
        stream = StringIO.StringIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == u""

    def test_bug1098990_b(self):
        import codecs, StringIO
        self.encoding = 'utf-8'
        s1 = u"aaaaaaaaaaaaaaaaaaaaaaaa\r\n"
        s2 = u"bbbbbbbbbbbbbbbbbbbbbbbb\r\n"
        s3 = u"stillokay:bbbbxx\r\n"
        s4 = u"broken!!!!badbad\r\n"
        s5 = u"againokay.\r\n"

        s = (s1+s2+s3+s4+s5).encode(self.encoding)
        stream = StringIO.StringIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == s4
        assert reader.readline() == s5
        assert reader.readline() == u""

    def test_seek_utf16le(self):
        # all codecs should be able to encode these
        import codecs, StringIO
        encoding = 'utf-16-le'
        s = u"%s\n%s\n" % (10*u"abc123", 10*u"def456")
        reader = codecs.getreader(encoding)(StringIO.StringIO(s.encode(encoding)))
        for t in xrange(5):
            # Test that calling seek resets the internal codec state and buffers
            reader.seek(0, 0)
            line = reader.readline()
            assert s[:len(line)] == line

    def test_unicode_internal_encode(self):
        import sys
        class U(unicode):
            pass
        enc = U(u"a").encode("unicode_internal")
        if sys.maxunicode == 65535: # UCS2 build
            if sys.byteorder == "big":
                assert enc == "\x00a"
            else:
                assert enc == "a\x00"
        elif len(u"\U00010098") == 1:
            # UCS4 build on a UCS4 CPython
            enc2 = u"\U00010098".encode("unicode_internal")
            if sys.byteorder == "big":
                assert enc == "\x00\x00\x00a"
                assert enc2 == "\x00\x01\x00\x98"
            else:
                assert enc == "a\x00\x00\x00"
                assert enc2 == "\x98\x00\x01\x00"
        else:
            # UCS4 build on a UCS2 CPython
            if sys.byteorder == "big":
                assert enc == "\x00\x00\x00a"
            else:
                assert enc == "a\x00\x00\x00"

    def test_unicode_internal_decode(self):
        import sys, _codecs, array
        if sys.maxunicode == 65535: # UCS2 build
            if sys.byteorder == "big":
                bytes = "\x00a"
            else:
                bytes = "a\x00"
        else: # UCS4 build
            if sys.byteorder == "big":
                bytes = "\x00\x00\x00a"
                bytes2 = "\x00\x01\x00\x98"
            else:
                bytes = "a\x00\x00\x00"
                bytes2 = "\x98\x00\x01\x00"
            assert bytes2.decode("unicode_internal") == u"\U00010098"
        assert bytes.decode("unicode_internal") == u"a"
        assert _codecs.unicode_internal_decode(array.array('c', bytes))[0] == u"a"
        if '__pypy__' in sys.modules:
            assert _codecs.unicode_internal_decode(memoryview(bytes))[0] == u"a"

    def test_raw_unicode_escape(self):
        assert unicode("\u0663", "raw-unicode-escape") == u"\u0663"
        assert u"\u0663".encode("raw-unicode-escape") == "\u0663"

    def test_escape_decode(self):
        test = 'a\n\\b\x00c\td\u2045'.encode('string_escape')
        assert test.decode('string_escape') =='a\n\\b\x00c\td\u2045'
        assert '\\077'.decode('string_escape') == '?'
        assert '\\100'.decode('string_escape') == '@'
        assert '\\253'.decode('string_escape') == chr(0253)
        assert '\\312'.decode('string_escape') == chr(0312)

    def test_escape_decode_wrap_around(self):
        assert '\\400'.decode('string_escape') == chr(0)

    def test_escape_decode_ignore_invalid(self):
        assert '\\9'.decode('string_escape') == '\\9'
        assert '\\01'.decode('string_escape') == chr(01)
        assert '\\0f'.decode('string_escape') == chr(0) + 'f'
        assert '\\08'.decode('string_escape') == chr(0) + '8'

    def test_escape_decode_errors(self):
        raises(ValueError, br"\x".decode, 'string_escape')
        raises(ValueError, br"[\x]".decode, 'string_escape')
        raises(ValueError, br"\x0".decode, 'string_escape')
        raises(ValueError, br"[\x0]".decode, 'string_escape')

    def test_unicode_escape_decode_errors(self):
        from _codecs import unicode_escape_decode, raw_unicode_escape_decode
        for decode in [unicode_escape_decode, raw_unicode_escape_decode]:
            for c, d in ('u', 4), ('U', 4):
                for i in range(d):
                    raises(UnicodeDecodeError, decode, "\\" + c + "0"*i)
                    raises(UnicodeDecodeError, decode, "[\\" + c + "0"*i + "]")
                    data = "[\\" + c + "0"*i + "]\\" + c + "0"*i
                    assert decode(data, "ignore") == (u"[]", len(data))
                    assert decode(data, "replace") == (u"[\ufffd]\ufffd", len(data))
            raises(UnicodeDecodeError, decode, r"\U00110000")
            assert decode(r"\U00110000", "ignore") == (u"", 10)
            assert decode(r"\U00110000", "replace") == (u"\ufffd", 10)
        exc = raises(UnicodeDecodeError, unicode_escape_decode, b"\u1z32z3", 'strict')
        assert str(exc.value) == r"'unicodeescape' codec can't decode bytes in position 0-2: truncated \uXXXX escape"
        exc = raises(UnicodeDecodeError, raw_unicode_escape_decode, b"\u1z32z3", 'strict')
        assert str(exc.value) == r"'rawunicodeescape' codec can't decode bytes in position 0-2: truncated \uXXXX"
        exc = raises(UnicodeDecodeError, raw_unicode_escape_decode, b"\U1z32z3", 'strict')
        assert str(exc.value) == r"'rawunicodeescape' codec can't decode bytes in position 0-2: truncated \uXXXX"

    def test_escape_encode(self):
        assert '"'.encode('string_escape') == '"'
        assert "'".encode('string_escape') == "\\'"

    def test_decode_utf8_different_case(self):
        constant = u"a"
        assert constant.encode("utf-8") == constant.encode("UTF-8")

    def test_codec_wrong_result(self):
        import _codecs
        def search_function(encoding):
            def f(input, errors="strict"):
                return 42
            if encoding == 'test.mytestenc':
                return (f, f, None, None)
            return None
        _codecs.register(search_function)
        raises(TypeError, b"hello".decode, "test.mytestenc")
        raises(TypeError, u"hello".encode, "test.mytestenc")

    def test_one_arg_encoder(self):
        import _codecs
        def search_function(encoding):
            def encode_one(u):
                return (b'foo', len(u))
            def decode_one(u):
                return (u'foo', len(u))
            if encoding == 'onearg':
                return (encode_one, decode_one, None, None)
            return None
        _codecs.register(search_function)
        assert u"hello".encode("onearg") == b'foo'
        assert b"hello".decode("onearg") == u'foo'
        assert _codecs.encode(u"hello", "onearg") == b'foo'
        assert _codecs.decode(b"hello", "onearg") == u'foo'

    def test_cpytest_decode(self):
        import codecs
        assert codecs.decode(b'\xe4\xf6\xfc', 'latin-1') == u'\xe4\xf6\xfc'
        raises(TypeError, codecs.decode)
        assert codecs.decode(b'abc') == u'abc'
        raises(UnicodeDecodeError, codecs.decode, b'\xff', 'ascii')

    def test_bad_errorhandler_return(self):
        import codecs
        def baddecodereturn1(exc):
            return 42
        codecs.register_error("test.baddecodereturn1", baddecodereturn1)
        raises(TypeError, b"\xff".decode, "ascii", "test.baddecodereturn1")
        raises(TypeError, b"\\".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, b"\\x0".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, b"\\x0y".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, b"\\Uffffeeee".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, b"\\uyyyy".decode, "raw-unicode-escape", "test.baddecodereturn1")

    def test_cpy_bug1175396(self):
        import codecs, StringIO
        s = [
            '<%!--===================================================\r\n',
            '    BLOG index page: show recent articles,\r\n',
            '    today\'s articles, or articles of a specific date.\r\n',
            '========================================================--%>\r\n',
            '<%@inputencoding="ISO-8859-1"%>\r\n',
            '<%@pagetemplate=TEMPLATE.y%>\r\n',
            '<%@import=import frog.util, frog%>\r\n',
            '<%@import=import frog.objects%>\r\n',
            '<%@import=from frog.storageerrors import StorageError%>\r\n',
            '<%\r\n',
            '\r\n',
            'import logging\r\n',
            'log=logging.getLogger("Snakelets.logger")\r\n',
            '\r\n',
            '\r\n',
            'user=self.SessionCtx.user\r\n',
            'storageEngine=self.SessionCtx.storageEngine\r\n',
            '\r\n',
            '\r\n',
            'def readArticlesFromDate(date, count=None):\r\n',
            '    entryids=storageEngine.listBlogEntries(date)\r\n',
            '    entryids.reverse() # descending\r\n',
            '    if count:\r\n',
            '        entryids=entryids[:count]\r\n',
            '    try:\r\n',
            '        return [ frog.objects.BlogEntry.load(storageEngine, date, Id) for Id in entryids ]\r\n',
            '    except StorageError,x:\r\n',
            '        log.error("Error loading articles: "+str(x))\r\n',
            '        self.abort("cannot load articles")\r\n',
        ]
        stream = StringIO.StringIO("".join(s).encode("utf7"))
        assert b"aborrt" not in stream.getvalue()
        reader = codecs.getreader("utf7")(stream)
        for (i, line) in enumerate(reader):
            assert line == s[i]

    def test_buffer_encode(self):
        import _codecs, array
        assert _codecs.readbuffer_encode(array.array('c', 'spam')) == ('spam', 4)
        exc = raises(TypeError, _codecs.charbuffer_encode, array.array('c', 'spam'))
        assert "must be string or read-only character buffer, not array.array" in str(exc.value)
        assert _codecs.readbuffer_encode(u"test") == ('test', 4)
        assert _codecs.charbuffer_encode(u"test") == ('test', 4)

    def test_utf8sig(self):
        import codecs
        d = codecs.getincrementaldecoder("utf-8-sig")()
        s = u"spam"
        assert d.decode(s.encode("utf-8-sig")) == s

    def test_decoder_state(self):
        import codecs
        encoding = 'utf16'
        u = 'abc123'
        s = u.encode(encoding)
        for i in range(len(u) + 1):
            d = codecs.getincrementalencoder(encoding)()
            part1 = d.encode(u[:i])
            state = d.getstate()
            d = codecs.getincrementalencoder(encoding)()
            d.setstate(state)
            part2 = d.encode(u[i:], True)
            assert s == part1 + part2

    def test_escape_decode_escaped_newline(self):
        import _codecs
        s = b'\\\n'
        decoded = _codecs.unicode_escape_decode(s)[0]
        assert decoded == ''

    def test_charmap_decode_1(self):
        import codecs
        assert codecs.charmap_encode(u'xxx') == (b'xxx', 3)
        assert codecs.charmap_encode(u'xxx', 'strict', {ord('x'): b'XX'}) == (b'XXXXXX', 3)

        res = codecs.charmap_decode(b"\x00\x01\x02", "replace", u"ab")
        assert res == (u"ab\ufffd", 3)
        res = codecs.charmap_decode(b"\x00\x01\x02", "replace", u"ab\ufffe")
        assert res == (u'ab\ufffd', 3)

    def test_decode_errors(self):
        import sys
        if sys.maxunicode > 0xffff:
            try:
                b"\x00\x00\x00\x00\x00\x11\x11\x00".decode("unicode_internal")
            except UnicodeDecodeError as ex:
                assert "unicode_internal" == ex.encoding
                assert b"\x00\x00\x00\x00\x00\x11\x11\x00" == ex.object
                assert ex.start == 4
                assert ex.end == 8
            else:
                raise Exception("DID NOT RAISE")

    def test_errors(self):
        import codecs
        assert codecs.replace_errors(UnicodeEncodeError(
            "ascii", u"\u3042", 0, 1, "ouch")) == (u"?", 1)
        assert codecs.replace_errors(UnicodeDecodeError(
            "ascii", b"\xff", 0, 1, "ouch")) == (u"\ufffd", 1)
        assert codecs.replace_errors(UnicodeTranslateError(
            u"\u3042", 0, 1, "ouch")) == (u"\ufffd", 1)

        assert codecs.replace_errors(UnicodeEncodeError(
            "ascii", u"\u3042\u3042", 0, 2, "ouch")) == (u"??", 2)
        assert codecs.replace_errors(UnicodeDecodeError(
            "ascii", b"\xff\xff", 0, 2, "ouch")) == (u"\ufffd", 2)
        assert codecs.replace_errors(UnicodeTranslateError(
            u"\u3042\u3042", 0, 2, "ouch")) == (u"\ufffd\ufffd", 2)

        class BadStartUnicodeEncodeError(UnicodeEncodeError):
            def __init__(self):
                UnicodeEncodeError.__init__(self, "ascii", u"", 0, 1, "bad")
                self.start = []

        # A UnicodeEncodeError object with a bad object attribute
        class BadObjectUnicodeEncodeError(UnicodeEncodeError):
            def __init__(self):
                UnicodeEncodeError.__init__(self, "ascii", u"", 0, 1, "bad")
                self.object = []

        # A UnicodeDecodeError object without an end attribute
        class NoEndUnicodeDecodeError(UnicodeDecodeError):
            def __init__(self):
                UnicodeDecodeError.__init__(self, "ascii", b"", 0, 1, "bad")
                del self.end

        # A UnicodeDecodeError object with a bad object attribute
        class BadObjectUnicodeDecodeError(UnicodeDecodeError):
            def __init__(self):
                UnicodeDecodeError.__init__(self, "ascii", b"", 0, 1, "bad")
                self.object = []

        # A UnicodeTranslateError object without a start attribute
        class NoStartUnicodeTranslateError(UnicodeTranslateError):
            def __init__(self):
                UnicodeTranslateError.__init__(self, u"", 0, 1, "bad")
                del self.start

        # A UnicodeTranslateError object without an end attribute
        class NoEndUnicodeTranslateError(UnicodeTranslateError):
            def __init__(self):
                UnicodeTranslateError.__init__(self,  u"", 0, 1, "bad")
                del self.end

        # A UnicodeTranslateError object without an object attribute
        class NoObjectUnicodeTranslateError(UnicodeTranslateError):
            def __init__(self):
                UnicodeTranslateError.__init__(self, u"", 0, 1, "bad")
                del self.object

        import codecs
        raises(TypeError, codecs.replace_errors, BadObjectUnicodeEncodeError())
        raises(TypeError, codecs.replace_errors, 42)
        # "replace" complains about the wrong exception type
        raises(TypeError, codecs.replace_errors, UnicodeError("ouch"))
        raises(TypeError, codecs.replace_errors, BadObjectUnicodeEncodeError())
        raises(TypeError, codecs.replace_errors, BadObjectUnicodeDecodeError()
        )
        # With the correct exception, "replace" returns an "?" or u"\ufffd" replacement

    def test_decode_ignore(self):
        assert b'\xff'.decode('utf-7', 'ignore') == ''
        assert b'\x00'.decode('unicode-internal', 'ignore') == ''

    def test_backslashreplace(self):
        import sys
        sin = u"a\xac\u1234\u20ac\u8000\U0010ffff"
        if sys.maxunicode > 65535:
            expected_ascii = b"a\\xac\\u1234\\u20ac\\u8000\\U0010ffff"
            expected_8859 = b"a\xac\\u1234\xa4\\u8000\\U0010ffff"
        else:
            expected_ascii = b"a\\xac\\u1234\\u20ac\\u8000\\udbff\\udfff"
            expected_8859 = b"a\xac\\u1234\xa4\\u8000\\udbff\\udfff"
        assert sin.encode('ascii', 'backslashreplace') == expected_ascii
        assert sin.encode("iso-8859-15", "backslashreplace") == expected_8859

    def test_badhandler(self):
        import codecs
        results = ( 42, u"foo", (1,2,3), (u"foo", 1, 3), (u"foo", None), (u"foo",), ("foo", 1, 3), ("foo", None), ("foo",) )
        encs = ("ascii", "latin-1", "iso-8859-1", "iso-8859-15")

        for res in results:
            codecs.register_error("test.badhandler", lambda x: res)
            for enc in encs:
                raises(
                    TypeError,
                    u"\u3042".encode,
                    enc,
                    "test.badhandler"
                )
            for (enc, bytes) in (
                ("utf-8", b"\xff"),
                ("ascii", b"\xff"),
                ("utf-7", b"+x-"),
                ("unicode-internal", b"\x00"),
            ):
                raises(
                    TypeError,
                    bytes.decode,
                    enc,
                    "test.badhandler"
                )

    def test_badhandler_longindex(self):
        import codecs
        import sys
        errors = 'test.badhandler_longindex'
        codecs.register_error(errors, lambda x: (u'', sys.maxsize + 1))
        # CPython raises OverflowError here
        raises((IndexError, OverflowError), b'apple\x92ham\x93spam'.decode, 'utf-8', errors)

    def test_unicode_internal(self):
        import codecs
        import sys
        try:
            b'\x00'.decode('unicode-internal')
        except UnicodeDecodeError:
            pass
        else:
            raise Exception("DID NOT RAISE")

        res = b"\x00\x00\x00\x00\x00".decode("unicode-internal", "replace")
        if sys.maxunicode > 65535:
            assert res == u"\u0000\ufffd"    # UCS4 build
        else:
            assert res == u"\x00\x00\ufffd"  # UCS2 build

        res = "\x00\x00\x00\x00\x00".decode("unicode-internal", "ignore")
        if sys.maxunicode > 65535:
            assert res == u"\u0000"   # UCS4 build
        else:
            assert res == u"\x00\x00" # UCS2 build

        def handler_unicodeinternal(exc):
            if not isinstance(exc, UnicodeDecodeError):
                raise TypeError("don't know how to handle %r" % exc)
            return (u"\x01", 5)
        codecs.register_error("test.hui", handler_unicodeinternal)
        res = b"\x00\x00\x00\x00\x00".decode("unicode-internal", "test.hui")
        if sys.maxunicode > 65535:
            assert res == u"\u0000\u0001"   # UCS4 build
        else:
            assert res == u"\x00\x00\x01" # UCS2 build

        def handler1(exc):
            if not isinstance(exc, UnicodeEncodeError) \
               and not isinstance(exc, UnicodeDecodeError):
                raise TypeError("don't know how to handle %r" % exc)
            l = [u"<%d>" % ord(exc.object[pos]) for pos in xrange(exc.start, exc.end)]
            return (u"[%s]" % u"".join(l), exc.end)
        codecs.register_error("test.handler1", handler1)
        assert b"\\u3042\u3xxx".decode("unicode-escape", "test.handler1") == \
            u"\u3042[<92><117><51>]xxx"

    def test_unicode_internal_error_handler_infinite_loop(self):
        import codecs
        class MyException(Exception):
            pass
        seen = [0]
        def handler_unicodeinternal(exc):
            if not isinstance(exc, UnicodeDecodeError):
                raise TypeError("don't know how to handle %r" % exc)
            seen[0] += 1
            if seen[0] == 20:   # stop the 20th time this is called
                raise MyException
            return (u"\x01", 4)   # 4 < len(input), so will try and fail again
        codecs.register_error("test.inf", handler_unicodeinternal)
        try:
            "\x00\x00\x00\x00\x00".decode("unicode-internal", "test.inf")
        except MyException:
            pass
        else:
            raise AssertionError("should have gone into infinite loop")

    def test_encode_error_bad_handler(self):
        import codecs
        codecs.register_error("test.bad_handler", lambda e: (repl, 1))
        assert u"xyz".encode("latin-1", "test.bad_handler") == "xyz"
        repl = u"\u1234"
        raises(UnicodeEncodeError, u"\u5678".encode, "latin-1",
               "test.bad_handler")
        repl = u"\u00E9"
        s = u"\u5678".encode("latin-1", "test.bad_handler")
        assert s == '\xe9'

    def test_charmap_encode(self):
        assert 'xxx'.encode('charmap') == 'xxx'

        import codecs
        exc = raises(TypeError, codecs.charmap_encode, u'\xff', "replace",  {0xff: 300})
        assert str(exc.value) == 'character mapping must be in range(256)'
        exc = raises(TypeError, codecs.charmap_encode, u'\xff', "replace",  {0xff: u'a'})
        assert str(exc.value) == 'character mapping must return integer, None or str'
        raises(UnicodeError, codecs.charmap_encode, u"\xff", "replace", {0xff: None})

    def test_charmap_encode_replace(self):
        charmap = dict([ (ord(c), 2*c.upper()) for c in "abcdefgh"])
        charmap[ord("?")] = "XYZ"
        import codecs
        sin = u"abcDEF"
        sout = codecs.charmap_encode(sin, "replace", charmap)[0]
        assert sout == "AABBCCXYZXYZXYZ"

    def test_charmap_decode_2(self):
        assert 'foo'.decode('charmap') == 'foo'

    def test_charmap_build(self):
        import codecs
        assert codecs.charmap_build(u'123456') == {49: 0, 50: 1, 51: 2,
                                                   52: 3, 53: 4, 54: 5}

    def test_utf7_start_end_in_exception(self):
        try:
            '+IC'.decode('utf-7')
        except UnicodeDecodeError as exc:
            assert exc.start == 0
            assert exc.end == 3

    def test_utf7_surrogate(self):
        assert '+3ADYAA-'.decode('utf-7') == u'\udc00\ud800'

    def test_utf7_errors(self):
        import codecs
        tests = [
            (b'a\xffb', u'a\ufffdb'),
            (b'a+IK', u'a\ufffd'),
            (b'a+IK-b', u'a\ufffdb'),
            (b'a+IK,b', u'a\ufffdb'),
            (b'a+IKx', u'a\u20ac\ufffd'),
            (b'a+IKx-b', u'a\u20ac\ufffdb'),
            (b'a+IKwgr', u'a\u20ac\ufffd'),
            (b'a+IKwgr-b', u'a\u20ac\ufffdb'),
            (b'a+IKwgr,', u'a\u20ac\ufffd'),
            (b'a+IKwgr,-b', u'a\u20ac\ufffd-b'),
            (b'a+IKwgrB', u'a\u20ac\u20ac\ufffd'),
            (b'a+IKwgrB-b', u'a\u20ac\u20ac\ufffdb'),
            (b'a+/,+IKw-b', u'a\ufffd\u20acb'),
            (b'a+//,+IKw-b', u'a\ufffd\u20acb'),
            (b'a+///,+IKw-b', u'a\uffff\ufffd\u20acb'),
            (b'a+////,+IKw-b', u'a\uffff\ufffd\u20acb'),
            (b'a+2AE\xe1b', u'a\ufffdb'),
            (b'a+2AEA-b', u'a\ufffdb'),
            (b'a+2AH-b', u'a\ufffdb'),
        ]
        for raw, expected in tests:
            raises(UnicodeDecodeError, codecs.utf_7_decode, raw, 'strict', True)
            assert raw.decode('utf-7', 'replace') == expected

    def test_utf_16_encode_decode(self):
        import codecs, sys
        x = u'123abc'
        if sys.byteorder == 'big':
            assert codecs.getencoder('utf-16')(x) == (
                    b'\xfe\xff\x001\x002\x003\x00a\x00b\x00c', 6)
            assert codecs.getdecoder('utf-16')(
                    b'\xfe\xff\x001\x002\x003\x00a\x00b\x00c') == (x, 14)
        else:
            assert codecs.getencoder('utf-16')(x) == (
                    b'\xff\xfe1\x002\x003\x00a\x00b\x00c\x00', 6)
            assert codecs.getdecoder('utf-16')(
                    b'\xff\xfe1\x002\x003\x00a\x00b\x00c\x00') == (x, 14)

    def test_unicode_escape(self):
        assert u'\\'.encode('unicode-escape') == '\\\\'
        assert b'\\\\'.decode('unicode-escape') == u'\\'
        assert u'\ud801'.encode('unicode-escape') == '\\ud801'
        assert u'\u0013'.encode('unicode-escape') == '\\x13'

    def test_mbcs(self):
        import sys
        if sys.platform != 'win32':
            return
        toencode = u'caf\xe9', 'caf\xe9'
        try:
            # test for non-latin1 codepage, more general test needed
            import _winreg
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                        r'System\CurrentControlSet\Control\Nls\CodePage')
            if _winreg.QueryValueEx(key, 'ACP')[0] == u'1255':  # non-latin1
                toencode = u'caf\xbf','caf\xbf'
        except:
            assert False, 'cannot test mbcs on this windows system, check code page'
        assert u'test'.encode('mbcs') == 'test'
        assert toencode[0].encode('mbcs') == toencode[1]
        assert u'\u040a'.encode('mbcs') == '?'  # some cyrillic letter
        assert 'cafx\e9'.decode('mbcs') == u'cafx\e9'

    def test_bad_handler_string_result(self):
        import _codecs
        def f(exc):
            return ('foo', exc.end)
        _codecs.register_error("test.test_codecs_not_a_string", f)
        raises(TypeError, u'\u1234'.encode, 'ascii',
               'test.test_codecs_not_a_string')

    def test_decode_bytearray(self):
        import _codecs
        b = bytearray()
        assert _codecs.ascii_decode(b) == (u'', 0)
        assert _codecs.latin_1_decode(b) == (u'', 0)
        assert _codecs.utf_7_decode(b) == (u'', 0)
        assert _codecs.utf_8_decode(b) == (u'', 0)
        assert _codecs.utf_16_be_decode(b) == (u'', 0)
        assert _codecs.utf_16_decode(b) == (u'', 0)
        assert _codecs.utf_16_le_decode(b) == (u'', 0)
        assert _codecs.utf_16_ex_decode(b) == (u'', 0, 0)
        assert _codecs.utf_32_decode(b) == (u'', 0)
        assert _codecs.utf_32_be_decode(b) == (u'', 0)
        assert _codecs.utf_32_le_decode(b) == (u'', 0)
        assert _codecs.utf_32_ex_decode(b) == (u'', 0, 0)
        assert _codecs.charmap_decode(b) == (u'', 0)
        assert _codecs.unicode_escape_decode(b) == (u'', 0)
        assert _codecs.raw_unicode_escape_decode(b) == (u'', 0)
        assert _codecs.unicode_internal_decode(b) == (u'', 0)

    def test_xmlcharrefreplace(self):
        r = u'\u1234\u0080\u2345\u0079\u00AB'.encode('latin1', 'xmlcharrefreplace')
        assert r == '&#4660;\x80&#9029;y\xab'
        r = u'\u1234\u0080\u2345\u0079\u00AB'.encode('ascii', 'xmlcharrefreplace')
        assert r == '&#4660;&#128;&#9029;y&#171;'

    def test_errorhandler_collection(self):
        import _codecs
        errors = []
        def record_error(exc):
            if not isinstance(exc, UnicodeEncodeError):
                raise TypeError("don't know how to handle %r" % exc)
            errors.append(exc.object[exc.start:exc.end])
            return (u'', exc.end)
        _codecs.register_error("test.record", record_error)

        sin = u"\xac\u1234\u1234\u20ac\u8000"
        assert sin.encode("ascii", "test.record") == ""
        assert errors == [sin]

        errors = []
        assert sin.encode("latin-1", "test.record") == "\xac"
        assert errors == [u'\u1234\u1234\u20ac\u8000']

        errors = []
        assert sin.encode("iso-8859-15", "test.record") == "\xac\xa4"
        assert errors == [u'\u1234\u1234', u'\u8000']

    def test_last_byte_handler(self):
        # issue bb-2389
        import _codecs
        _codecs.register_error('custom_replace', lambda exc: (u'\ufffd', exc.start+1))
        for s, res in ((b"WORD\xe3\xab",
                            (u'WORD\ufffd\ufffd', u'WORD\ufffd')),
                       (b"\xef\xbb\xbfWORD\xe3\xabWORD2",
                            (u'\ufeffWORD\ufffd\ufffdWORD2',
                             u'\ufeffWORD\ufffdWORD2'))):
            r = s.decode('utf8', 'replace')
            assert r == res[1]
            r = s.decode('utf8', 'custom_replace')
            assert r == res[0]
