import sys

class AppTestCodecs:
    spaceconfig = {
        "usemodules": ['unicodedata', 'struct', 'binascii'],
    }

    def test_register_noncallable(self):
        import _codecs
        raises(TypeError, _codecs.register, 1)

    def test_bigU_codecs(self):
        u = '\U00010001\U00020002\U00030003\U00040004\U00050005'
        for encoding in ('utf-8', 'utf-16', 'utf-16-le', 'utf-16-be',
                         'utf-32', 'utf-32-le', 'utf-32-be',
                         'raw_unicode_escape',
                         'unicode_escape', 'unicode_internal'):
            assert str(u.encode(encoding),encoding) == u

    def test_ucs4(self):
        x = '\U00100000'
        y = x.encode("raw-unicode-escape").decode("raw-unicode-escape")
        assert x == y

    def test_named_unicode(self):
        assert str(b'\\N{SPACE}','unicode-escape') == u" "
        raises( UnicodeDecodeError, str,b'\\N{SPACE','unicode-escape')
        raises( UnicodeDecodeError, str,b'\\NSPACE}','unicode-escape')
        raises( UnicodeDecodeError, str,b'\\NSPACE','unicode-escape')
        raises( UnicodeDecodeError, str,b'\\N','unicode-escape')
        assert  str(b'\\N{SPACE}\\N{SPACE}','unicode-escape') == u"  "
        assert  str(b'\\N{SPACE}a\\N{SPACE}','unicode-escape') == u" a "
        assert b"\\N{foo}xx".decode("unicode-escape", "ignore") == u"xx"
        assert 1 <= len(u"\N{CJK UNIFIED IDEOGRAPH-20000}") <= 2

    def test_literals(self):
        raises(SyntaxError, eval, 'u\'\\Uffffffff\'')

    def test_insecure_pickle(self):
        import pickle
        insecure = [b"abc", b"2 + 2", # not quoted
                    #"'abc' + 'def'", # not a single quoted string
                    b"'abc", # quote is not closed
                    b"'abc\"", # open quote and close quote don't match
                    b"'abc'   ?", # junk after close quote
                    b"'\\'", # trailing backslash
                    # some tests of the quoting rules
                    #"'abc\"\''",
                    #"'\\\\a\'\'\'\\\'\\\\\''",
                    ]
        for s in insecure:
            buf = b"S" + s + b"\012p0\012."
            raises (ValueError, pickle.loads, buf)

    def test_unicodedecodeerror(self):
        assert str(UnicodeDecodeError(
            "ascii", b"g\xfcrk", 1, 2, "ouch")) == "'ascii' codec can't decode byte 0xfc in position 1: ouch"

        assert str(UnicodeDecodeError(
            "ascii", b"g\xfcrk", 1, 3, "ouch")) == "'ascii' codec can't decode bytes in position 1-2: ouch"

    def test_unicodetranslateerror(self):
        import sys
        assert str(UnicodeTranslateError(
            "g\xfcrk", 1, 2, "ouch"))== "can't translate character '\\xfc' in position 1: ouch"

        assert str(UnicodeTranslateError(
            "g\u0100rk", 1, 2, "ouch"))== "can't translate character '\\u0100' in position 1: ouch"

        assert str(UnicodeTranslateError(
            "g\uffffrk", 1, 2, "ouch"))== "can't translate character '\\uffff' in position 1: ouch"

        if sys.maxunicode > 0xffff and len(chr(0x10000)) == 1:
            assert str(UnicodeTranslateError(
                "g\U00010000rk", 1, 2, "ouch"))== "can't translate character '\\U00010000' in position 1: ouch"

        assert str(UnicodeTranslateError(
            "g\xfcrk", 1, 3, "ouch"))=="can't translate characters in position 1-2: ouch"

    def test_unicodeencodeerror(self):
        import sys
        assert str(UnicodeEncodeError(
            "ascii", "g\xfcrk", 1, 2, "ouch"))=="'ascii' codec can't encode character '\\xfc' in position 1: ouch"

        assert str(UnicodeEncodeError(
            "ascii", "g\xfcrk", 1, 4, "ouch"))== "'ascii' codec can't encode characters in position 1-3: ouch"

        assert str(UnicodeEncodeError(
            "ascii", "\xfcx", 0, 1, "ouch"))=="'ascii' codec can't encode character '\\xfc' in position 0: ouch"

        assert str(UnicodeEncodeError(
            "ascii", "\u0100x", 0, 1, "ouch"))=="'ascii' codec can't encode character '\\u0100' in position 0: ouch"

        assert str(UnicodeEncodeError(
            "ascii", "\uffffx", 0, 1, "ouch"))=="'ascii' codec can't encode character '\\uffff' in position 0: ouch"
        if sys.maxunicode > 0xffff and len(chr(0x10000)) == 1:
            assert str(UnicodeEncodeError(
                "ascii", "\U00010000x", 0, 1, "ouch")) =="'ascii' codec can't encode character '\\U00010000' in position 0: ouch"

    def test_indexerror(self):
        import _codecs
        test =   b"\\"     # trailing backslash
        raises (ValueError, _codecs.escape_decode, test)

    def test_charmap_decode(self):
        from _codecs import charmap_decode
        import sys
        assert charmap_decode(b'', 'strict', 'blablabla') == ('', 0)
        assert charmap_decode(b'xxx') == ('xxx', 3)
        assert charmap_decode(b'xxx', 'strict', {ord('x'): 'XX'}) == ('XXXXXX', 3)
        map = tuple([chr(i) for i in range(256)])
        assert charmap_decode(b'xxx\xff', 'strict', map) == ('xxx\xff', 4)

        exc = raises(TypeError, charmap_decode, b'\xff', "strict",  {0xff: b'a'})
        assert str(exc.value) == "character mapping must return integer, None or unicode"
        raises(TypeError, charmap_decode, b'\xff', "strict",  {0xff: 0x110000})
        assert (charmap_decode(b"\x00\x01\x02", "strict",
                               {0: 0x10FFFF, 1: ord('b'), 2: ord('c')}) ==
                u"\U0010FFFFbc", 3)
        assert (charmap_decode(b"\x00\x01\x02", "strict",
                               {0: u'\U0010FFFF', 1: u'b', 2: u'c'}) ==
                u"\U0010FFFFbc", 3)

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
        assert unicode_escape_encode('abc') == ('abc'.encode('unicode_escape'), 3)
        assert unicode_escape_decode(b'abc') == (b'abc'.decode('unicode_escape'), 3)
        assert unicode_escape_decode(b'\\x61\\x62\\x63') == ('abc', 12)


class AppTestPartialEvaluation:
    spaceconfig = dict(usemodules=['array',])

    def test_partial_utf8(self):
        import _codecs
        encoding = 'utf-8'
        check_partial = [
                "\x00",
                "\x00",
                "\x00\xff",
                "\x00\xff",
                "\x00\xff\u07ff",
                "\x00\xff\u07ff",
                "\x00\xff\u07ff",
                "\x00\xff\u07ff\u0800",
                "\x00\xff\u07ff\u0800",
                "\x00\xff\u07ff\u0800",
                "\x00\xff\u07ff\u0800\uffff",
                "\x00\xff\u07ff\u0800\uffff",
                "\x00\xff\u07ff\u0800\uffff",
                "\x00\xff\u07ff\u0800\uffff",
                "\x00\xff\u07ff\u0800\uffff\U00010000",
            ]

        buffer = b''
        result = ""
        for (c, partialresult) in zip("\x00\xff\u07ff\u0800\uffff\U00010000".encode(encoding), check_partial):
            buffer += bytes([c])
            res = _codecs.utf_8_decode(buffer,'strict',False)
            if res[1] >0 :
                buffer = b''
            result += res[0]
            assert result == partialresult

    def test_partial_utf16(self):
        import _codecs
        encoding = 'utf-16'
        check_partial = [
                    "", # first byte of BOM read
                    "", # second byte of BOM read => byteorder known
                    "",
                    "\x00",
                    "\x00",
                    "\x00\xff",
                    "\x00\xff",
                    "\x00\xff\u0100",
                    "\x00\xff\u0100",
                    "\x00\xff\u0100\uffff",
                    "\x00\xff\u0100\uffff",
                    "\x00\xff\u0100\uffff",
                    "\x00\xff\u0100\uffff",
                    "\x00\xff\u0100\uffff\U00010000",
                ]
        buffer = b''
        result = ""
        for (c, partialresult) in zip("\x00\xff\u0100\uffff\U00010000".encode(encoding), check_partial):
            buffer += bytes([c])
            res = _codecs.utf_16_decode(buffer,'strict',False)
            if res[1] >0 :
                buffer = b''
            result += res[0]
            assert result == partialresult

    def test_bug1098990_a(self):
        import codecs, io
        self.encoding = 'utf-8'
        s1 = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\r\n"
        s2 = "offending line: ladfj askldfj klasdj fskla dfzaskdj fasklfj laskd fjasklfzzzzaa%whereisthis!!!\r\n"
        s3 = "next line.\r\n"

        s = (s1+s2+s3).encode(self.encoding)
        stream = io.BytesIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == ""

    def test_bug1098990_b(self):
        import codecs, io
        self.encoding = 'utf-8'
        s1 = "aaaaaaaaaaaaaaaaaaaaaaaa\r\n"
        s2 = "bbbbbbbbbbbbbbbbbbbbbbbb\r\n"
        s3 = "stillokay:bbbbxx\r\n"
        s4 = "broken!!!!badbad\r\n"
        s5 = "againokay.\r\n"

        s = (s1+s2+s3+s4+s5).encode(self.encoding)
        stream = io.BytesIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == s4
        assert reader.readline() == s5
        assert reader.readline() == ""

    def test_seek_utf16le(self):
        # all codecs should be able to encode these
        import codecs, io
        encoding = 'utf-16-le'
        s = "%s\n%s\n" % (10*"abc123", 10*"def456")
        reader = codecs.getreader(encoding)(io.BytesIO(s.encode(encoding)))
        for t in range(5):
            # Test that calling seek resets the internal codec state and buffers
            reader.seek(0, 0)
            line = reader.readline()
            assert s[:len(line)] == line

    def test_unicode_internal_encode(self):
        import sys
        class U(str):
            pass
        enc = U("a").encode("unicode_internal")
        if sys.maxunicode == 65535: # UCS2 build
            if sys.byteorder == "big":
                assert enc == b"\x00a"
            else:
                assert enc == b"a\x00"
        elif len("\U00010098") == 1:
            # UCS4 build on a UCS4 CPython
            enc2 = "\U00010098".encode("unicode_internal")
            if sys.byteorder == "big":
                assert enc == b"\x00\x00\x00a"
                assert enc2 == b"\x00\x01\x00\x98"
            else:
                assert enc == b"a\x00\x00\x00"
                assert enc2 == b"\x98\x00\x01\x00"
        else:
            # UCS4 build on a UCS2 CPython
            if sys.byteorder == "big":
                assert enc == b"\x00\x00\x00a"
            else:
                assert enc == b"a\x00\x00\x00"

    def test_unicode_internal_decode(self):
        import sys, _codecs, array
        if sys.maxunicode == 65535: # UCS2 build
            if sys.byteorder == "big":
                bytes = b"\x00a"
            else:
                bytes = b"a\x00"
        else: # UCS4 build
            if sys.byteorder == "big":
                bytes = b"\x00\x00\x00a"
                bytes2 = b"\x00\x01\x00\x98"
            else:
                bytes = b"a\x00\x00\x00"
                bytes2 = b"\x98\x00\x01\x00"
            assert bytes2.decode("unicode_internal") == "\U00010098"
        assert bytes.decode("unicode_internal") == "a"
        assert _codecs.unicode_internal_decode(array.array('b', bytes))[0] == u"a"
        assert _codecs.unicode_internal_decode(memoryview(bytes))[0] == u"a"

        # This codec accepts bytes and unicode on both sides
        _codecs.unicode_internal_decode(u'\0\0\0\0')
        _codecs.unicode_internal_decode(b'\0\0\0\0')
        _codecs.unicode_internal_encode(u'\0\0\0\0')
        _codecs.unicode_internal_encode(b'\0\0\0\0')

    def test_raw_unicode_escape(self):
        import _codecs
        assert str(b"\u0663", "raw-unicode-escape") == "\u0663"
        assert "\u0663".encode("raw-unicode-escape") == b"\u0663"
        assert _codecs.raw_unicode_escape_decode(r"\u1234") == ("\u1234", 6)

    def test_escape_decode(self):
        import _codecs
        test = _codecs.escape_encode(b'a\n\\b\x00c\td\u2045')[0]
        assert _codecs.escape_decode(test)[0] == b'a\n\\b\x00c\td\u2045'
        assert _codecs.escape_decode(b'\\077')[0] == b'?'
        assert _codecs.escape_decode(b'\\100')[0] == b'@'
        assert _codecs.escape_decode(b'\\253')[0] == bytes([0o253])
        assert _codecs.escape_decode(b'\\312')[0] == bytes([0o312])

    def test_escape_decode_wrap_around(self):
        import _codecs
        assert _codecs.escape_decode(b'\\400')[0] == b'\0'

    def test_escape_decode_ignore_invalid(self):
        import _codecs
        assert _codecs.escape_decode(b'\\9')[0] == b'\\9'
        assert _codecs.escape_decode(b'\\01')[0] == b'\x01'
        assert _codecs.escape_decode(b'\\0f')[0] == b'\0' + b'f'
        assert _codecs.escape_decode(b'\\08')[0] == b'\0' + b'8'

    def test_escape_decode_errors(self):
        import _codecs
        raises(ValueError, _codecs.escape_decode, br"\x")
        raises(ValueError, _codecs.escape_decode, br"[\x]")
        raises(ValueError, _codecs.escape_decode, br"\x0")
        raises(ValueError, _codecs.escape_decode, br"[\x0]")

    def test_unicode_escape_decode_errors(self):
        from _codecs import unicode_escape_decode, raw_unicode_escape_decode
        for decode in [unicode_escape_decode, raw_unicode_escape_decode]:
            for c, d in ('u', 4), ('U', 4):
                for i in range(d):
                    raises(UnicodeDecodeError, decode,
                                      "\\" + c + "0"*i)
                    raises(UnicodeDecodeError, decode,
                                      "[\\" + c + "0"*i + "]")
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
        import _codecs
        assert _codecs.escape_encode(b'"')[0] == b'"'
        assert _codecs.escape_encode(b"'")[0] == b"\\'"

    def test_decode_utf8_different_case(self):
        constant = "a"
        assert constant.encode("utf-8") == constant.encode("UTF-8")

    def test_codec_wrong_result(self):
        import _codecs
        def search_function(encoding):
            def f(input, errors="strict"):
                return 42
            print(encoding)
            if encoding == 'test.mytestenc':
                return (f, f, None, None)
            return None
        _codecs.register(search_function)
        raises(TypeError, b"hello".decode, "test.mytestenc")
        raises(TypeError, "hello".encode, "test.mytestenc")

    def test_cpytest_decode(self):
        import codecs
        assert codecs.decode(b'\xe4\xf6\xfc', 'latin-1') == '\xe4\xf6\xfc'
        raises(TypeError, codecs.decode)
        assert codecs.decode(b'abc') == 'abc'
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
        import codecs, io
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
        stream = io.BytesIO("".join(s).encode("utf7"))
        assert b"aborrt" not in stream.getvalue()
        reader = codecs.getreader("utf7")(stream)
        for (i, line) in enumerate(reader):
            assert line == s[i]

    def test_buffer_encode(self):
        import _codecs, array
        assert (_codecs.readbuffer_encode(array.array('b', b'spam')) ==
                (b'spam', 4))
        assert _codecs.readbuffer_encode(u"test") == (b'test', 4)
        assert _codecs.readbuffer_encode("") ==  (b"", 0)

    def test_utf8sig(self):
        import codecs
        d = codecs.getincrementaldecoder("utf-8-sig")()
        s = "spam"
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
        assert codecs.charmap_encode('xxx') == (b'xxx', 3)
        assert codecs.charmap_encode('xxx', 'strict', {ord('x'): b'XX'}) == (b'XXXXXX', 3)

        res = codecs.charmap_decode(b"\x00\x01\x02", "replace", "ab")
        assert res == ("ab\ufffd", 3)
        res = codecs.charmap_decode(b"\x00\x01\x02", "replace", "ab\ufffe")
        assert res == ('ab\ufffd', 3)

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
            "ascii", "\u3042", 0, 1, "ouch")) == ("?", 1)
        assert codecs.replace_errors(UnicodeDecodeError(
            "ascii", b"\xff", 0, 1, "ouch")) == ("\ufffd", 1)
        assert codecs.replace_errors(UnicodeTranslateError(
            "\u3042", 0, 1, "ouch")) == ("\ufffd", 1)

        assert codecs.replace_errors(UnicodeEncodeError(
            "ascii", "\u3042\u3042", 0, 2, "ouch")) == ("??", 2)
        assert codecs.replace_errors(UnicodeDecodeError(
            "ascii", b"\xff\xff", 0, 2, "ouch")) == ("\ufffd", 2)
        assert codecs.replace_errors(UnicodeTranslateError(
            "\u3042\u3042", 0, 2, "ouch")) == ("\ufffd\ufffd", 2)

        class BadStartUnicodeEncodeError(UnicodeEncodeError):
            def __init__(self):
                UnicodeEncodeError.__init__(self, "ascii", "", 0, 1, "bad")
                self.start = []

        # A UnicodeEncodeError object with a bad object attribute
        class BadObjectUnicodeEncodeError(UnicodeEncodeError):
            def __init__(self):
                UnicodeEncodeError.__init__(self, "ascii", "", 0, 1, "bad")
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
                UnicodeTranslateError.__init__(self, "", 0, 1, "bad")
                del self.start

        # A UnicodeTranslateError object without an end attribute
        class NoEndUnicodeTranslateError(UnicodeTranslateError):
            def __init__(self):
                UnicodeTranslateError.__init__(self,  "", 0, 1, "bad")
                del self.end

        # A UnicodeTranslateError object without an object attribute
        class NoObjectUnicodeTranslateError(UnicodeTranslateError):
            def __init__(self):
                UnicodeTranslateError.__init__(self, "", 0, 1, "bad")
                del self.object

        import codecs
        raises(TypeError, codecs.replace_errors, BadObjectUnicodeEncodeError())
        raises(TypeError, codecs.replace_errors, 42)
        # "replace" complains about the wrong exception type
        raises(TypeError, codecs.replace_errors, UnicodeError("ouch"))
        raises(TypeError, codecs.replace_errors, BadObjectUnicodeEncodeError())
        raises(TypeError, codecs.replace_errors, BadObjectUnicodeDecodeError()
        )
        # With the correct exception, "replace" returns an "?" or "\ufffd" replacement

    def test_decode_ignore(self):
        assert b'\xff'.decode('utf-7', 'ignore') == ''
        assert b'\x00'.decode('unicode-internal', 'ignore') == ''

    def test_backslashreplace(self):
        assert 'a\xac\u1234\u20ac\u8000'.encode('ascii', 'backslashreplace') == b'a\\xac\u1234\u20ac\u8000'

    def test_namereplace(self):
        assert 'a\xac\u1234\u20ac\u8000'.encode('ascii', 'namereplace') == (
            b'a\\N{NOT SIGN}\\N{ETHIOPIC SYLLABLE SEE}\\N{EURO SIGN}'
            b'\\N{CJK UNIFIED IDEOGRAPH-8000}')

    def test_surrogateescape(self):
        assert b'a\x80b'.decode('utf-8', 'surrogateescape') == 'a\udc80b'
        assert 'a\udc80b'.encode('utf-8', 'surrogateescape') == b'a\x80b'
        for enc in ('utf-8', 'ascii', 'latin-1', 'charmap'):
            assert '\udcc3'.encode(enc, 'surrogateescape') == b'\xc3'

    def test_surrogatepass_handler(self):
        import _codecs
        assert _codecs.lookup_error("surrogatepass")
        assert ("abc\ud800def".encode("utf-8", "surrogatepass") ==
                b"abc\xed\xa0\x80def")
        assert (b"abc\xed\xa0\x80def".decode("utf-8", "surrogatepass") ==
                "abc\ud800def")
        assert ('surrogate:\udcff'.encode("utf-8", "surrogatepass") ==
                b'surrogate:\xed\xb3\xbf')
        assert (b'surrogate:\xed\xb3\xbf'.decode("utf-8", "surrogatepass") ==
                'surrogate:\udcff')
        raises(UnicodeDecodeError, b"abc\xed\xa0".decode, "utf-8",
               "surrogatepass")
        raises(UnicodeDecodeError, b"abc\xed\xa0z".decode, "utf-8",
               "surrogatepass")

    def test_badhandler(self):
        import codecs
        results = ( 42, "foo", (1,2,3), ("foo", 1, 3), ("foo", None), ("foo",), ("foo", 1, 3), ("foo", None), ("foo",) )
        encs = ("ascii", "latin-1", "iso-8859-1", "iso-8859-15")

        for res in results:
            codecs.register_error("test.badhandler", lambda x: res)
            for enc in encs:
                raises(
                    TypeError,
                    "\u3042".encode,
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
        codecs.register_error(errors, lambda x: ('', sys.maxsize + 1))
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
            assert res == "\u0000\ufffd"    # UCS4 build
        else:
            assert res == "\x00\x00\ufffd"  # UCS2 build

        res = b"\x00\x00\x00\x00\x00".decode("unicode-internal", "ignore")
        if sys.maxunicode > 65535:
            assert res == "\u0000"   # UCS4 build
        else:
            assert res == "\x00\x00" # UCS2 build

        def handler_unicodeinternal(exc):
            if not isinstance(exc, UnicodeDecodeError):
                raise TypeError("don't know how to handle %r" % exc)
            return ("\x01", 1)
        codecs.register_error("test.hui", handler_unicodeinternal)
        res = b"\x00\x00\x00\x00\x00".decode("unicode-internal", "test.hui")
        if sys.maxunicode > 65535:
            assert res == "\u0000\u0001\u0000"   # UCS4 build
        else:
            assert res == "\x00\x00\x01\x00\x00" # UCS2 build

        def handler1(exc):
            if not isinstance(exc, UnicodeEncodeError) \
               and not isinstance(exc, UnicodeDecodeError):
                raise TypeError("don't know how to handle %r" % exc)
            l = [u"<%d>" % exc.object[pos] for pos in range(exc.start, exc.end)]
            return (u"[%s]" % u"".join(l), exc.end)
        codecs.register_error("test.handler1", handler1)
        assert b"\\u3042\u3xxx".decode("unicode-escape", "test.handler1") == \
            u"\u3042[<92><117><51>]xxx"

    def test_encode_error_bad_handler(self):
        import codecs
        codecs.register_error("test.bad_handler", lambda e: (repl, 1))
        assert "xyz".encode("latin-1", "test.bad_handler") == b"xyz"
        repl = "\u1234"
        raises(UnicodeEncodeError, "\u5678".encode, "latin-1",
               "test.bad_handler")
        repl = "\u00E9"
        s = "\u5678".encode("latin-1", "test.bad_handler")
        assert s == b'\xe9'

    def test_charmap_encode(self):
        assert 'xxx'.encode('charmap') == b'xxx'

        import codecs
        exc = raises(TypeError, codecs.charmap_encode, u'\xff', "replace",  {0xff: 300})
        assert str(exc.value) == 'character mapping must be in range(256)'
        exc = raises(TypeError, codecs.charmap_encode, u'\xff', "replace",  {0xff: u'a'})
        assert str(exc.value) == 'character mapping must return integer, None or str'
        raises(UnicodeError, codecs.charmap_encode, u"\xff", "replace", {0xff: None})

    def test_charmap_encode_replace(self):
        charmap = dict([(c, bytes([c, c]).upper()) for c in b"abcdefgh"])
        charmap[ord("?")] = b"XYZ"
        import codecs
        sin = "abcDEF"
        sout = codecs.charmap_encode(sin, "replace", charmap)[0]
        assert sout == b"AABBCCXYZXYZXYZ"

    def test_charmap_decode_2(self):
        assert b'foo'.decode('charmap') == 'foo'

    def test_charmap_build(self):
        import codecs
        assert codecs.charmap_build('123456') == {49: 0, 50: 1, 51: 2,
                                                   52: 3, 53: 4, 54: 5}

    def test_utf7_start_end_in_exception(self):
        try:
            b'+IC'.decode('utf-7')
        except UnicodeDecodeError as exc:
            assert exc.start == 0
            assert exc.end == 3

    def test_utf7_surrogate(self):
        assert b'+3ADYAA-'.decode('utf-7') == '\udc00\ud800'

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
        x = '123abc'
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
        import _codecs
        assert '\\'.encode('unicode-escape') == b'\\\\'
        assert b'\\\\'.decode('unicode-escape') == '\\'
        assert '\ud801'.encode('unicode-escape') == b'\\ud801'
        assert '\u0013'.encode('unicode-escape') == b'\\x13'
        assert _codecs.unicode_escape_decode(r"\u1234") == ("\u1234", 6)

    def test_mbcs(self):
        import sys
        if sys.platform != 'win32':
            return
        toencode = u'caf\xe9', b'caf\xe9'
        try:
            # test for non-latin1 codepage, more general test needed
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r'System\CurrentControlSet\Control\Nls\CodePage')
            if winreg.QueryValueEx(key, 'ACP')[0] == u'1255':  # non-latin1
                toencode = u'caf\xbf',b'caf\xbf'
        except:
            assert False, 'cannot test mbcs on this windows system, check code page'
        assert u'test'.encode('mbcs') == b'test'
        assert toencode[0].encode('mbcs') == toencode[1]
        assert u'\u040a'.encode('mbcs') == b'?'  # some cyrillic letter
        assert b'cafx\e9'.decode('mbcs') == u'cafx\e9'

    def test_handler_string_result(self):
        import _codecs
        def f(exc):
            return (b'foo', exc.end)
        _codecs.register_error("test.test_codecs_not_a_string", f)
        result = '\u1234'.encode('ascii', 'test.test_codecs_not_a_string')
        assert result == b'foo'

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

    def test_unicode_internal_warnings(self):
        import codecs, warnings
        warnings.simplefilter("always")
        encoder = codecs.getencoder("unicode_internal")
        decoder = codecs.getdecoder("unicode_internal")
        warning_msg = "unicode_internal codec has been deprecated"
        with warnings.catch_warnings(record=True) as w:
            try:
                encoder(42)
            except TypeError:
                pass
            assert len(w) == 1
            assert str(w[0].message) == warning_msg
            assert w[0].category == DeprecationWarning

        with warnings.catch_warnings(record=True) as w:
            try:
                decoder(42)
            except TypeError:
                pass
            assert len(w) == 0

        with warnings.catch_warnings(record=True) as w:
            encoded_abc = encoder("abc")[0]
            assert len(w) == 1
            assert str(w[0].message)== warning_msg
            assert w[0].category == DeprecationWarning

        with warnings.catch_warnings(record=True) as w:
            print(type(encoded_abc))
            decoder(encoded_abc)
            assert len(w) == 1
            assert str(w[0].message) == warning_msg
            assert w[0].category == DeprecationWarning
