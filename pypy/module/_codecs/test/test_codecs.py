import autopath
from pypy.conftest import gettestobjspace
from pypy.module._codecs.app_codecs import unicode_escape_encode,\
     charmap_encode, unicode_escape_decode


class AppTestCodecs:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('unicodedata',))
        cls.space = space

    def test_register_noncallable(self):
        import _codecs
        raises(TypeError, _codecs.register, 1)

    def test_bigU_codecs(self):
        import sys
        oldmaxunicode = sys.maxunicode
        if sys.maxunicode <= 0xffff:
            return # this test cannot run on UCS2 builds
        u = u'\U00010001\U00020002\U00030003\U00040004\U00050005'
        for encoding in ('utf-8', 'utf-16', 'utf-16-le', 'utf-16-be',
                         'raw_unicode_escape',
                         'unicode_escape', 'unicode_internal'):
            assert unicode(u.encode(encoding),encoding) == u
        sys.maxunicode = oldmaxunicode

    def test_ucs4(self):
        import sys
        oldmaxunicode = sys.maxunicode
        if sys.maxunicode <= 0xffff:
            sys.maxunicode = 0xffffffff
        x = u'\U00100000'
        y = x.encode("raw-unicode-escape").decode("raw-unicode-escape")
        assert x == y 
        sys.maxunicode = oldmaxunicode

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
        raises(UnicodeError, eval, 'u\'\\Uffffffff\'')

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
        
        if sys.maxunicode > 0xffff:
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
        if sys.maxunicode > 0xffff:
            assert str(UnicodeEncodeError(
                "ascii", u"\U00010000x", 0, 1, "ouch")) =="'ascii' codec can't encode character u'\\U00010000' in position 0: ouch"
    
    def test_indexerror(self):
        test =   "\\"     # trailing backslash
             
        raises (ValueError, test.decode,'string-escape')

    def test_charmap_decode(self):
        from _codecs import charmap_decode
        assert charmap_decode('', 'strict', 'blablabla') == ('', 0)
        assert charmap_decode('xxx') == ('xxx', 3)
        assert charmap_decode('xxx', 'strict', {ord('x'): u'XX'}) == ('XXXXXX', 3)
        map = tuple([unichr(i) for i in range(256)])
        assert charmap_decode('xxx\xff', 'strict', map) == (u'xxx\xff', 4)


class AppTestPartialEvaluation:

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
            ]
            
        buffer = ''
        result = u""
        for (c, partialresult) in zip(u"\x00\xff\u07ff\u0800\uffff".encode(encoding), check_partial):
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
                ]
        buffer = ''
        result = u""
        for (c, partialresult) in zip(u"\x00\xff\u0100\uffff".encode(encoding), check_partial):
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
        enc = u"a".encode("unicode_internal")
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
        import sys
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


    def test_decode_utf8_different_case(self):
        constant = u"a"
        assert constant.encode("utf-8") == constant.encode("UTF-8")

    def test_codec_wrong_result(self):
        import _codecs
        def search_function(encoding):
            def f(input, errors="strict"):
                return 42
            print encoding
            if encoding == 'test.mytestenc':
                return (f, f, None, None)
            return None
        _codecs.register(search_function)
        raises(TypeError, "hello".decode, "test.mytestenc")
        raises(TypeError, u"hello".encode, "test.mytestenc")

    def test_cpytest_decode(self):
        import codecs
        assert codecs.decode('\xe4\xf6\xfc', 'latin-1') == u'\xe4\xf6\xfc'
        raises(TypeError, codecs.decode)
        assert codecs.decode('abc') == u'abc'
        raises(UnicodeDecodeError, codecs.decode, '\xff', 'ascii')

    def test_bad_errorhandler_return(self):
        import codecs
        def baddecodereturn1(exc):
            return 42
        codecs.register_error("test.baddecodereturn1", baddecodereturn1)
        raises(TypeError, "\xff".decode, "ascii", "test.baddecodereturn1")
        raises(TypeError, "\\".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, "\\x0".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, "\\x0y".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, "\\Uffffeeee".decode, "unicode-escape", "test.baddecodereturn1")
        raises(TypeError, "\\uyyyy".decode, "raw-unicode-escape", "test.baddecodereturn1")

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
        assert "aborrt" not in stream.getvalue()
        reader = codecs.getreader("utf7")(stream)
        for (i, line) in enumerate(reader):
            assert line == s[i]

    def test_array(self):
        import _codecs, array
        _codecs.readbuffer_encode(array.array('c', 'spam')) == ('spam', 4)

    def test_utf8sig(self):
        import codecs
        d = codecs.getincrementaldecoder("utf-8-sig")()
        s = u"spam"
        assert d.decode(s.encode("utf-8-sig")) == s

    def test_escape_decode_escaped_newline(self):
        import _codecs
        s = '\\\n'
        decoded = _codecs.unicode_escape_decode(s)[0]
        assert decoded == ''

    def test_charmap_decode(self):
        import codecs
        res = codecs.charmap_decode("\x00\x01\x02", "replace", u"ab")
        assert res == (u"ab\ufffd", 3)
        res = codecs.charmap_decode("\x00\x01\x02", "replace", u"ab\ufffe")
        assert res == (u'ab\ufffd', 3)

    def test_decode_errors(self):
        import sys
        if sys.maxunicode > 0xffff:
            try:
                "\x00\x00\x00\x00\x00\x11\x11\x00".decode("unicode_internal")
            except UnicodeDecodeError, ex:
                assert "unicode_internal" == ex.encoding
                assert "\x00\x00\x00\x00\x00\x11\x11\x00" == ex.object
                assert ex.start == 4
                assert ex.end == 8
            else:
                raise Exception("DID NOT RAISE")

    def test_errors(self):
        import codecs
        assert (
            codecs.replace_errors(UnicodeEncodeError("ascii", u"\u3042", 0, 1, "ouch"))) == (
            (u"?", 1)
        )
        assert (
            codecs.replace_errors(UnicodeDecodeError("ascii", "\xff", 0, 1, "ouch"))) == (
            (u"\ufffd", 1)
        )
        assert (
            codecs.replace_errors(UnicodeTranslateError(u"\u3042", 0, 1, "ouch"))) == (
            (u"\ufffd", 1)
        )
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
                UnicodeDecodeError.__init__(self, "ascii", "", 0, 1, "bad")
                del self.end

        # A UnicodeDecodeError object with a bad object attribute
        class BadObjectUnicodeDecodeError(UnicodeDecodeError):
            def __init__(self):
                UnicodeDecodeError.__init__(self, "ascii", "", 0, 1, "bad")
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
        assert '\xff'.decode('utf-7', 'ignore') == ''
        assert '\x00'.decode('unicode-internal', 'ignore') == ''

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
                ("utf-8", "\xff"),
                ("ascii", "\xff"),
                ("utf-7", "+x-"),
                ("unicode-internal", "\x00"),
            ):
                raises(
                    TypeError,
                    bytes.decode,
                    enc,
                    "test.badhandler"
                )

    def test_unicode_internal(self):
        import codecs
        import sys
        try:
            '\x00'.decode('unicode-internal')
        except UnicodeDecodeError:
            pass
        else:
            raise Exception("DID NOT RAISE")

        res = "\x00\x00\x00\x00\x00".decode("unicode-internal", "replace")
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
            return (u"\x01", 1)
        codecs.register_error("test.hui", handler_unicodeinternal)
        res = "\x00\x00\x00\x00\x00".decode("unicode-internal", "test.hui")
        if sys.maxunicode > 65535:
            assert res == u"\u0000\u0001\u0000"   # UCS4 build
        else:
            assert res == u"\x00\x00\x01\x00\x00" # UCS2 build

    def test_charmap_encode(self):
        assert 'xxx'.encode('charmap') == 'xxx'

    def test_charmap_decode(self):
        assert 'foo'.decode('charmap') == 'foo'

    def test_utf7_start_end_in_exception(self):
        try:
            '+IC'.decode('utf-7')
        except UnicodeDecodeError, exc:
            assert exc.start == 0
            assert exc.end == 3

    def test_utf_16_encode_decode(self):
        import codecs
        x = u'123abc'
        assert codecs.getencoder('utf-16')(x) == ('\xff\xfe1\x002\x003\x00a\x00b\x00c\x00', 6)
        assert codecs.getdecoder('utf-16')('\xff\xfe1\x002\x003\x00a\x00b\x00c\x00') == (x, 14)

    def test_unicode_escape(self):        
        assert u'\\'.encode('unicode-escape') == '\\\\'
        assert '\\\\'.decode('unicode-escape') == u'\\'

    def test_mbcs(self):
        import sys
        if sys.platform != 'win32':
            return
        assert u'test'.encode('mbcs') == 'test'
        assert u'caf\xe9'.encode('mbcs') == 'caf\xe9'
        assert u'\u040a'.encode('mbcs') == '?' # some cyrillic letter
        assert 'cafx\e9'.decode('mbcs') == u'cafx\e9'


class TestDirect:
    def test_charmap_encode(self):
        assert charmap_encode(u'xxx') == ('xxx', 3)
        assert charmap_encode(u'xxx', 'strict', {ord('x'): 'XX'}) ==  ('XXXXXX', 6)

    def test_unicode_escape(self):
        assert unicode_escape_encode(u'abc') == (u'abc'.encode('unicode_escape'), 3)
        assert unicode_escape_decode('abc') == (u'abc'.decode('unicode_escape'), 3)
        assert unicode_escape_decode('\\x61\\x62\\x63') == (u'abc', 12)
