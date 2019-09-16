import sys

class AppTestCodecs:
    spaceconfig = {
        "usemodules": ['unicodedata', 'struct', 'binascii', '_warnings'],
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
            assert str(u.encode(encoding), encoding) == u

    def test_ucs4(self):
        x = u'\U00100000'
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
            raises ((ValueError, pickle.UnpicklingError), pickle.loads, buf)

    def test_unicodedecodeerror(self):
        assert str(UnicodeDecodeError(
            "ascii", b"g\xfcrk", 1, 2, "ouch")) == "'ascii' codec can't decode byte 0xfc in position 1: ouch"

        assert str(UnicodeDecodeError(
            "ascii", b"g\xfcrk", 1, 3, "ouch")) == "'ascii' codec can't decode bytes in position 1-2: ouch"

    def test_unicodedecodeerror_utf8(self):
        error = raises(UnicodeDecodeError, b'\xf6'.decode, "utf-8").value
        assert str(error) == "'utf-8' codec can't decode byte 0xf6 in position 0: invalid start byte"

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
        res = charmap_decode(b'xxx', 'strict', {ord('x'): 'XX'})
        assert  res == ('XXXXXX', 3)
        map = tuple([chr(i) for i in range(256)])
        assert charmap_decode(b'xxx\xff', 'strict', map) == ('xxx\xff', 4)

        exc = raises(TypeError, charmap_decode, b'\xff', "strict",  {0xff: b'a'})
        assert str(exc.value) == "character mapping must return integer, None or str"
        raises(TypeError, charmap_decode, b'\xff', "strict",  {0xff: 0x110000})
        assert (charmap_decode(b"\x00\x01\x02", "strict",
                               {0: 0x10FFFF, 1: ord('b'), 2: ord('c')}) ==
                (u"\U0010FFFFbc", 3))
        assert (charmap_decode(b"\x00\x01\x02", "strict",
                               {0: u'\U0010FFFF', 1: u'b', 2: u'c'}) ==
                (u"\U0010FFFFbc", 3))
        assert charmap_decode(b'\xff', "strict", {0xff: 0xd800}) == (u'\ud800', 1)

    def test_escape_decode(self):
        from _codecs import unicode_escape_decode as decode
        import sys
        if sys.version_info[0] < 3:
            assert decode('\\\x80') == (u'\\\x80', 2)
        else:
            assert decode('\\\x80') == (u'\\\xc2\x80', 3)

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
        lgt = 12
        assert unicode_escape_decode(b'\\x61\\x62\\x63') == ('abc', lgt)

    def test_unicode_replace(self):
        # CPython #8271: during the decoding of an invalid UTF-8 byte sequence,
        # only the start byte and the continuation byte(s) are now considered
        # invalid, instead of the number of bytes specified by the start byte.
        # See http://www.unicode.org/versions/Unicode5.2.0/ch03.pdf (page 42,
        # table 3-8, Row 2) for more information about the algorithm used.
        FFFD = '\ufffd'
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
            (b'\xf1\x80\x41\x42\x43', '\ufffd\x41\x42\x43'),
            (b'\xf1\x80\xff\x42\x43', '\ufffd\ufffd\x42\x43'),
            (b'\xf1\x80\xc2\x81\x43', '\ufffd\x81\x43'),
            (b'\x61\xF1\x80\x80\xE1\x80\xC2\x62\x80\x63\x80\xBF\x64',
             '\x61\uFFFD\uFFFD\uFFFD\x62\uFFFD\x63\uFFFD\uFFFD\x64'),
        ]
        for (seq, res) in sequences:
            raises(UnicodeDecodeError, seq.decode, 'utf-8', 'strict')
            uni = seq.decode('utf-8', 'replace')
            assert uni == res
            uni = (seq+b'b').decode('utf-8', 'replace')
            assert uni == res+'b'
            uni = seq.decode('utf-8', 'ignore')
            assert uni == res.replace('\uFFFD', '')

    def test_unexpected_end_of_data(self):
        """
        Test that an 'unexpected end of data' error is raised when the string
        ends after a start byte of a 2-, 3-, or 4-bytes sequence without having
        enough continuation bytes.  The incomplete sequence is replaced with a
        single U+FFFD when errors='replace'.
        E.g. in the sequence <F3 80 80>, F3 is the start byte of a 4-bytes
        sequence, but it's followed by only 2 valid continuation bytes and the
        last continuation bytes is missing.
        Note: the continuation bytes must be all valid, if one of them is
        invalid another error will be raised.
        """
        sequences = [
            'C2', 'DF',
            'E0 A0', 'E0 BF', 'E1 80', 'E1 BF', 'EC 80', 'EC BF',
            'ED 80', 'ED 9F', 'EE 80', 'EE BF', 'EF 80', 'EF BF',
            'F0 90', 'F0 BF', 'F0 90 80', 'F0 90 BF', 'F0 BF 80', 'F0 BF BF',
            'F1 80', 'F1 BF', 'F1 80 80', 'F1 80 BF', 'F1 BF 80', 'F1 BF BF',
            'F3 80', 'F3 BF', 'F3 80 80', 'F3 80 BF', 'F3 BF 80', 'F3 BF BF',
            'F4 80', 'F4 8F', 'F4 80 80', 'F4 80 BF', 'F4 8F 80', 'F4 8F BF'
        ]
        for seq in sequences:
            bseq = bytes(int(c, 16) for c in seq.split())
            exc = raises(UnicodeDecodeError, bseq.decode, 'utf-8')
            assert 'unexpected end of data' in str(exc.value)
            useq = bseq.decode('utf-8', 'replace')
            assert  useq == u'\ufffd', (bseq, useq)
            assert ((b'aaaa' + bseq + b'bbbb').decode('utf-8', 'replace') ==
                    u'aaaa\ufffdbbbb')
            assert bseq.decode('utf-8', 'ignore') == ''
            assert ((b'aaaa' + bseq + b'bbbb').decode('utf-8', 'ignore') ==
                    u'aaaabbbb')

    def test_invalid_cb_for_3bytes_seq(self):
        """
        Test that an 'invalid continuation byte' error is raised when the
        continuation byte(s) of a 3-bytes sequence are invalid.  When
        errors='replace', if the first continuation byte is valid, the first
        two bytes (start byte + 1st cb) are replaced by a single U+FFFD and the
        third byte is handled separately, otherwise only the start byte is
        replaced with a U+FFFD and the other continuation bytes are handled
        separately.
        E.g. in the sequence <E1 80 41>, E1 is the start byte of a 3-bytes
        sequence, 80 is a valid continuation byte, but 41 is not a valid cb
        because it's the ASCII letter 'A'.
        Note: when the start byte is E0 or ED, the valid ranges for the first
        continuation byte are limited to A0..BF and 80..9F respectively.
        Python 2 used to consider all the bytes in range 80..BF valid when the
        start byte was ED.  This is fixed in Python 3.
        """
        FFFD = '\ufffd'
        FFFDx2 = FFFD * 2
        sequences = [
            ('E0 00', FFFD+'\x00'), ('E0 7F', FFFD+'\x7f'), ('E0 80', FFFDx2),
            ('E0 9F', FFFDx2), ('E0 C0', FFFDx2), ('E0 FF', FFFDx2),
            ('E0 A0 00', FFFD+'\x00'), ('E0 A0 7F', FFFD+'\x7f'),
            ('E0 A0 C0', FFFDx2), ('E0 A0 FF', FFFDx2),
            ('E0 BF 00', FFFD+'\x00'), ('E0 BF 7F', FFFD+'\x7f'),
            ('E0 BF C0', FFFDx2), ('E0 BF FF', FFFDx2), ('E1 00', FFFD+'\x00'),
            ('E1 7F', FFFD+'\x7f'), ('E1 C0', FFFDx2), ('E1 FF', FFFDx2),
            ('E1 80 00', FFFD+'\x00'), ('E1 80 7F', FFFD+'\x7f'),
            ('E1 80 C0', FFFDx2), ('E1 80 FF', FFFDx2),
            ('E1 BF 00', FFFD+'\x00'), ('E1 BF 7F', FFFD+'\x7f'),
            ('E1 BF C0', FFFDx2), ('E1 BF FF', FFFDx2), ('EC 00', FFFD+'\x00'),
            ('EC 7F', FFFD+'\x7f'), ('EC C0', FFFDx2), ('EC FF', FFFDx2),
            ('EC 80 00', FFFD+'\x00'), ('EC 80 7F', FFFD+'\x7f'),
            ('EC 80 C0', FFFDx2), ('EC 80 FF', FFFDx2),
            ('EC BF 00', FFFD+'\x00'), ('EC BF 7F', FFFD+'\x7f'),
            ('EC BF C0', FFFDx2), ('EC BF FF', FFFDx2), ('ED 00', FFFD+'\x00'),
            ('ED 7F', FFFD+'\x7f'),
            ('ED A0', FFFDx2), ('ED BF', FFFDx2), # see note ^
            ('ED C0', FFFDx2), ('ED FF', FFFDx2), ('ED 80 00', FFFD+'\x00'),
            ('ED 80 7F', FFFD+'\x7f'), ('ED 80 C0', FFFDx2),
            ('ED 80 FF', FFFDx2), ('ED 9F 00', FFFD+'\x00'),
            ('ED 9F 7F', FFFD+'\x7f'), ('ED 9F C0', FFFDx2),
            ('ED 9F FF', FFFDx2), ('EE 00', FFFD+'\x00'),
            ('EE 7F', FFFD+'\x7f'), ('EE C0', FFFDx2), ('EE FF', FFFDx2),
            ('EE 80 00', FFFD+'\x00'), ('EE 80 7F', FFFD+'\x7f'),
            ('EE 80 C0', FFFDx2), ('EE 80 FF', FFFDx2),
            ('EE BF 00', FFFD+'\x00'), ('EE BF 7F', FFFD+'\x7f'),
            ('EE BF C0', FFFDx2), ('EE BF FF', FFFDx2), ('EF 00', FFFD+'\x00'),
            ('EF 7F', FFFD+'\x7f'), ('EF C0', FFFDx2), ('EF FF', FFFDx2),
            ('EF 80 00', FFFD+'\x00'), ('EF 80 7F', FFFD+'\x7f'),
            ('EF 80 C0', FFFDx2), ('EF 80 FF', FFFDx2),
            ('EF BF 00', FFFD+'\x00'), ('EF BF 7F', FFFD+'\x7f'),
            ('EF BF C0', FFFDx2), ('EF BF FF', FFFDx2),
        ]
        err = 'invalid continuation byte'
        for s, res in sequences:
            seq = bytes(int(c, 16) for c in s.split())
            exc = raises(UnicodeDecodeError, seq.decode, 'utf-8')
            assert err in str(exc.value)
            assert seq.decode('utf-8', 'replace') == res
            assert ((b'aaaa' + seq + b'bbbb').decode('utf-8', 'replace') ==
                         'aaaa' + res + 'bbbb')
            res = res.replace('\ufffd', '')
            assert seq.decode('utf-8', 'ignore') == res
            assert((b'aaaa' + seq + b'bbbb').decode('utf-8', 'ignore') ==
                          'aaaa' + res + 'bbbb')

    def test_invalid_cb_for_4bytes_seq(self):
        """
        Test that an 'invalid continuation byte' error is raised when the
        continuation byte(s) of a 4-bytes sequence are invalid.  When
        errors='replace',the start byte and all the following valid
        continuation bytes are replaced with a single U+FFFD, and all the bytes
        starting from the first invalid continuation bytes (included) are
        handled separately.
        E.g. in the sequence <E1 80 41>, E1 is the start byte of a 3-bytes
        sequence, 80 is a valid continuation byte, but 41 is not a valid cb
        because it's the ASCII letter 'A'.
        Note: when the start byte is E0 or ED, the valid ranges for the first
        continuation byte are limited to A0..BF and 80..9F respectively.
        However, when the start byte is ED, Python 2 considers all the bytes
        in range 80..BF valid.  This is fixed in Python 3.
        """
        FFFD = '\ufffd'
        FFFDx2 = FFFD * 2
        sequences = [
            ('F0 00', FFFD+'\x00'), ('F0 7F', FFFD+'\x7f'), ('F0 80', FFFDx2),
            ('F0 8F', FFFDx2), ('F0 C0', FFFDx2), ('F0 FF', FFFDx2),
            ('F0 90 00', FFFD+'\x00'), ('F0 90 7F', FFFD+'\x7f'),
            ('F0 90 C0', FFFDx2), ('F0 90 FF', FFFDx2),
            ('F0 BF 00', FFFD+'\x00'), ('F0 BF 7F', FFFD+'\x7f'),
            ('F0 BF C0', FFFDx2), ('F0 BF FF', FFFDx2),
            ('F0 90 80 00', FFFD+'\x00'), ('F0 90 80 7F', FFFD+'\x7f'),
            ('F0 90 80 C0', FFFDx2), ('F0 90 80 FF', FFFDx2),
            ('F0 90 BF 00', FFFD+'\x00'), ('F0 90 BF 7F', FFFD+'\x7f'),
            ('F0 90 BF C0', FFFDx2), ('F0 90 BF FF', FFFDx2),
            ('F0 BF 80 00', FFFD+'\x00'), ('F0 BF 80 7F', FFFD+'\x7f'),
            ('F0 BF 80 C0', FFFDx2), ('F0 BF 80 FF', FFFDx2),
            ('F0 BF BF 00', FFFD+'\x00'), ('F0 BF BF 7F', FFFD+'\x7f'),
            ('F0 BF BF C0', FFFDx2), ('F0 BF BF FF', FFFDx2),
            ('F1 00', FFFD+'\x00'), ('F1 7F', FFFD+'\x7f'), ('F1 C0', FFFDx2),
            ('F1 FF', FFFDx2), ('F1 80 00', FFFD+'\x00'),
            ('F1 80 7F', FFFD+'\x7f'), ('F1 80 C0', FFFDx2),
            ('F1 80 FF', FFFDx2), ('F1 BF 00', FFFD+'\x00'),
            ('F1 BF 7F', FFFD+'\x7f'), ('F1 BF C0', FFFDx2),
            ('F1 BF FF', FFFDx2), ('F1 80 80 00', FFFD+'\x00'),
            ('F1 80 80 7F', FFFD+'\x7f'), ('F1 80 80 C0', FFFDx2),
            ('F1 80 80 FF', FFFDx2), ('F1 80 BF 00', FFFD+'\x00'),
            ('F1 80 BF 7F', FFFD+'\x7f'), ('F1 80 BF C0', FFFDx2),
            ('F1 80 BF FF', FFFDx2), ('F1 BF 80 00', FFFD+'\x00'),
            ('F1 BF 80 7F', FFFD+'\x7f'), ('F1 BF 80 C0', FFFDx2),
            ('F1 BF 80 FF', FFFDx2), ('F1 BF BF 00', FFFD+'\x00'),
            ('F1 BF BF 7F', FFFD+'\x7f'), ('F1 BF BF C0', FFFDx2),
            ('F1 BF BF FF', FFFDx2), ('F3 00', FFFD+'\x00'),
            ('F3 7F', FFFD+'\x7f'), ('F3 C0', FFFDx2), ('F3 FF', FFFDx2),
            ('F3 80 00', FFFD+'\x00'), ('F3 80 7F', FFFD+'\x7f'),
            ('F3 80 C0', FFFDx2), ('F3 80 FF', FFFDx2),
            ('F3 BF 00', FFFD+'\x00'), ('F3 BF 7F', FFFD+'\x7f'),
            ('F3 BF C0', FFFDx2), ('F3 BF FF', FFFDx2),
            ('F3 80 80 00', FFFD+'\x00'), ('F3 80 80 7F', FFFD+'\x7f'),
            ('F3 80 80 C0', FFFDx2), ('F3 80 80 FF', FFFDx2),
            ('F3 80 BF 00', FFFD+'\x00'), ('F3 80 BF 7F', FFFD+'\x7f'),
            ('F3 80 BF C0', FFFDx2), ('F3 80 BF FF', FFFDx2),
            ('F3 BF 80 00', FFFD+'\x00'), ('F3 BF 80 7F', FFFD+'\x7f'),
            ('F3 BF 80 C0', FFFDx2), ('F3 BF 80 FF', FFFDx2),
            ('F3 BF BF 00', FFFD+'\x00'), ('F3 BF BF 7F', FFFD+'\x7f'),
            ('F3 BF BF C0', FFFDx2), ('F3 BF BF FF', FFFDx2),
            ('F4 00', FFFD+'\x00'), ('F4 7F', FFFD+'\x7f'), ('F4 90', FFFDx2),
            ('F4 BF', FFFDx2), ('F4 C0', FFFDx2), ('F4 FF', FFFDx2),
            ('F4 80 00', FFFD+'\x00'), ('F4 80 7F', FFFD+'\x7f'),
            ('F4 80 C0', FFFDx2), ('F4 80 FF', FFFDx2),
            ('F4 8F 00', FFFD+'\x00'), ('F4 8F 7F', FFFD+'\x7f'),
            ('F4 8F C0', FFFDx2), ('F4 8F FF', FFFDx2),
            ('F4 80 80 00', FFFD+'\x00'), ('F4 80 80 7F', FFFD+'\x7f'),
            ('F4 80 80 C0', FFFDx2), ('F4 80 80 FF', FFFDx2),
            ('F4 80 BF 00', FFFD+'\x00'), ('F4 80 BF 7F', FFFD+'\x7f'),
            ('F4 80 BF C0', FFFDx2), ('F4 80 BF FF', FFFDx2),
            ('F4 8F 80 00', FFFD+'\x00'), ('F4 8F 80 7F', FFFD+'\x7f'),
            ('F4 8F 80 C0', FFFDx2), ('F4 8F 80 FF', FFFDx2),
            ('F4 8F BF 00', FFFD+'\x00'), ('F4 8F BF 7F', FFFD+'\x7f'),
            ('F4 8F BF C0', FFFDx2), ('F4 8F BF FF', FFFDx2)
        ]
        err = 'invalid continuation byte'
        for s, res in sequences:
            seq = bytes(int(c, 16) for c in s.split())
            exc = raises(UnicodeDecodeError, seq.decode, 'utf-8')
            assert err in str(exc.value)
            assert seq.decode('utf-8', 'replace') == res
            assert ((b'aaaa' + seq + b'bbbb').decode('utf-8', 'replace') ==
                         'aaaa' + res + 'bbbb')
            res = res.replace('\ufffd', '')
            assert seq.decode('utf-8', 'ignore') == res
            assert((b'aaaa' + seq + b'bbbb').decode('utf-8', 'ignore') ==
                          'aaaa' + res + 'bbbb')


class AppTestPartialEvaluation:
    spaceconfig = dict(usemodules=['array',])

    def setup_class(cls):
        cls.w_appdirect = cls.space.wrap(cls.runappdirect)

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

        buffer = b''
        result = u""
        for (c, partialresult) in zip(u"\x00\xff\u07ff\u0800\uffff\U00010000".encode(encoding), check_partial):
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
        buffer = b''
        result = u""
        for (c, partialresult) in zip(u"\x00\xff\u0100\uffff\U00010000".encode(encoding), check_partial):
            buffer += bytes([c])
            res = _codecs.utf_16_decode(buffer,'strict',False)
            if res[1] >0 :
                buffer = b''
            result += res[0]
            assert result == partialresult

    def test_bug1098990_a(self):
        import codecs, io
        self.encoding = 'utf-8'
        s1 = u"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\r\n"
        s2 = u"offending line: ladfj askldfj klasdj fskla dfzaskdj fasklfj laskd fjasklfzzzzaa%whereisthis!!!\r\n"
        s3 = u"next line.\r\n"

        s = (s1+s2+s3).encode(self.encoding)
        stream = io.BytesIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == u""

    def test_bug1098990_b(self):
        import codecs, io
        self.encoding = 'utf-8'
        s1 = u"aaaaaaaaaaaaaaaaaaaaaaaa\r\n"
        s2 = u"bbbbbbbbbbbbbbbbbbbbbbbb\r\n"
        s3 = u"stillokay:bbbbxx\r\n"
        s4 = u"broken!!!!badbad\r\n"
        s5 = u"againokay.\r\n"

        s = (s1+s2+s3+s4+s5).encode(self.encoding)
        stream = io.BytesIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == s4
        assert reader.readline() == s5
        assert reader.readline() == u""

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
        import sys
        for decode in [unicode_escape_decode, raw_unicode_escape_decode]:
            for c, d in ('u', 4), ('U', 4):
                for i in range(d):
                    raises(UnicodeDecodeError, decode, "\\" + c + "0"*i)
                    raises(UnicodeDecodeError, decode, "[\\" + c + "0"*i + "]")
                    data = "[\\" + c + "0"*i + "]\\" + c + "0"*i
                    lgt = len(data)
                    assert decode(data, "ignore") == (u"[]", lgt)
                    assert decode(data, "replace") == (u"[\ufffd]\ufffd", lgt)
            raises(UnicodeDecodeError, decode, r"\U00110000")
            lgt = 10
            assert decode(r"\U00110000", "ignore") == (u"", lgt)
            assert decode(r"\U00110000", "replace") == (u"\ufffd", lgt)
        exc = raises(UnicodeDecodeError, unicode_escape_decode, b"\u1z32z3", 'strict')
        assert str(exc.value) == r"'unicodeescape' codec can't decode bytes in position 0-2: truncated \uXXXX escape"
        exc = raises(UnicodeDecodeError, raw_unicode_escape_decode, b"\u1z32z3", 'strict')
        assert str(exc.value) == r"'rawunicodeescape' codec can't decode bytes in position 0-2: truncated \uXXXX escape"
        exc = raises(UnicodeDecodeError, raw_unicode_escape_decode, b"\U1z32z3", 'strict')
        assert str(exc.value) == r"'rawunicodeescape' codec can't decode bytes in position 0-2: truncated \UXXXXXXXX escape"

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
            if encoding == 'test.mytestenc':
                return (f, f, None, None)
            return None
        _codecs.register(search_function)
        raises(TypeError, b"hello".decode, "test.mytestenc")
        raises(TypeError, "hello".encode, "test.mytestenc")

    def test_codec_wrapped_exception(self):
        import _codecs
        def search_function(encoding):
            def f(input, errors="strict"):
                raise to_raise
            if encoding == 'test.failingenc':
                return (f, f, None, None)
            return None
        _codecs.register(search_function)
        to_raise = RuntimeError('should be wrapped')
        exc = raises(RuntimeError, b"hello".decode, "test.failingenc")
        assert str(exc.value) == (
            "decoding with 'test.failingenc' codec failed "
            "(RuntimeError: should be wrapped)")
        exc = raises(RuntimeError, u"hello".encode, "test.failingenc")
        assert str(exc.value) == (
            "encoding with 'test.failingenc' codec failed "
            "(RuntimeError: should be wrapped)")
        #
        to_raise.attr = "don't wrap"
        exc = raises(RuntimeError, u"hello".encode, "test.failingenc")
        assert exc.value == to_raise
        #
        to_raise = RuntimeError("Should", "Not", "Wrap")
        exc = raises(RuntimeError, u"hello".encode, "test.failingenc")
        assert exc.value == to_raise

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
        assert codecs.decode(b'\xe4\xf6\xfc', 'latin-1') == '\xe4\xf6\xfc'
        raises(TypeError, codecs.decode)
        assert codecs.decode(b'abc') == 'abc'
        exc = raises(UnicodeDecodeError, codecs.decode, b'\xff', 'ascii')

        exc = raises(UnicodeDecodeError, codecs.decode, b'\xe0\x00', 'utf-8')
        assert 'invalid continuation byte' in exc.value.reason

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
        assert codecs.charmap_encode(u'xxx') == (b'xxx', 3)
        assert codecs.charmap_encode(u'xxx', 'strict', {ord('x'): b'XX'}) == (b'XXXXXX', 3)

        res = codecs.charmap_decode(b"\x00\x01\x02", "replace", u"ab")
        assert res == ("ab\ufffd", 3)
        res = codecs.charmap_decode(b"\x00\x01\x02", "replace", u"ab\ufffe")
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
            "ascii", u"\u3042", 0, 1, "ouch")) == (u"?", 1)
        assert codecs.replace_errors(UnicodeDecodeError(
            "ascii", b"\xff", 0, 1, "ouch")) == (u"\ufffd", 1)
        assert codecs.replace_errors(UnicodeTranslateError(
            "\u3042", 0, 1, "ouch")) == ("\ufffd", 1)

        assert codecs.replace_errors(UnicodeEncodeError(
            "ascii", "\u3042\u3042", 0, 2, "ouch")) == (u"??", 2)
        assert codecs.replace_errors(UnicodeDecodeError(
            "ascii", b"\xff\xff", 0, 2, "ouch")) == (u"\ufffd", 2)
        assert codecs.replace_errors(UnicodeTranslateError(
            "\u3042\u3042", 0, 2, "ouch")) == ("\ufffd\ufffd", 2)

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
        import sys, codecs
        sin = u"a\xac\u1234\u20ac\u8000\U0010ffff"
        if sys.maxunicode > 65535:
            expected_ascii = b"a\\xac\\u1234\\u20ac\\u8000\\U0010ffff"
            expected_8859 = b"a\xac\\u1234\xa4\\u8000\\U0010ffff"
        else:
            expected_ascii = b"a\\xac\\u1234\\u20ac\\u8000\\udbff\\udfff"
            expected_8859 = b"a\xac\\u1234\xa4\\u8000\\udbff\\udfff"
        assert sin.encode('ascii', 'backslashreplace') == expected_ascii
        assert sin.encode("iso-8859-15", "backslashreplace") == expected_8859

        assert 'a\xac\u1234\u20ac\u8000'.encode('ascii', 'backslashreplace') == b'a\\xac\u1234\u20ac\u8000'
        assert b'\x00\x60\x80'.decode(
            'ascii', 'backslashreplace') == u'\x00\x60\\x80'
        assert codecs.charmap_decode(
            b"\x00\x01\x02", "backslashreplace", "ab") == ("ab\\x02", 3)

    def test_namereplace(self):
        assert 'a\xac\u1234\u20ac\u8000'.encode('ascii', 'namereplace') == (
            b'a\\N{NOT SIGN}\\N{ETHIOPIC SYLLABLE SEE}\\N{EURO SIGN}'
            b'\\N{CJK UNIFIED IDEOGRAPH-8000}')
        assert '[\uDC80]'.encode('utf-8', 'namereplace') == b'[\\udc80]'

    def test_surrogateescape(self):
        uni = b"\xed\xb0\x80".decode("utf-8", "surrogateescape")
        assert uni == "\udced\udcb0\udc80"
        assert "\udce4\udceb\udcef\udcf6\udcfc".encode("latin-1",
                             "surrogateescape") == b"\xe4\xeb\xef\xf6\xfc"
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
        assert u'\ud8ae'.encode('utf_16_be', 'surrogatepass') == b'\xd8\xae'
        assert (u'\U0000d8ae'.encode('utf-32-be', 'surrogatepass') ==
                b'\x00\x00\xd8\xae')
        assert (u'\x80\ud800'.encode('utf8', 'surrogatepass') ==
                b'\xc2\x80\xed\xa0\x80')
        assert b'\xd8\x03\xdf\xff\xdc\x80\x00A'.decode('utf_16_be',
                 'surrogatepass') == u'\U00010fff\udc80A'

    def test_badandgoodsurrogatepassexceptions(self):
        import codecs
        surrogatepass_errors = codecs.lookup_error('surrogatepass')
        # "surrogatepass" complains about a non-exception passed in
        raises(TypeError, surrogatepass_errors, 42)
        # "surrogatepass" complains about the wrong exception types
        raises(TypeError, surrogatepass_errors, UnicodeError("ouch"))
        # "surrogatepass" can not be used for translating
        raises(TypeError, surrogatepass_errors,
               UnicodeTranslateError("\ud800", 0, 1, "ouch"))
        # Use the correct exception
        for enc in ("utf-8", "utf-16le", "utf-16be", "utf-32le", "utf-32be"):
            raises(UnicodeEncodeError, surrogatepass_errors,
                   UnicodeEncodeError(enc, "a", 0, 1, "ouch"))
            raises(UnicodeDecodeError, surrogatepass_errors,
                   UnicodeDecodeError(enc, "a".encode(enc), 0, 1, "ouch"))
        for s in ("\ud800", "\udfff", "\ud800\udfff"):
            raises(UnicodeEncodeError, surrogatepass_errors,
                   UnicodeEncodeError("ascii", s, 0, len(s), "ouch"))
        tests = [
            ("utf-8", "\ud800", b'\xed\xa0\x80', 3),
            ("utf-16le", "\ud800", b'\x00\xd8', 2),
            ("utf-16be", "\ud800", b'\xd8\x00', 2),
            ("utf-32le", "\ud800", b'\x00\xd8\x00\x00', 4),
            ("utf-32be", "\ud800", b'\x00\x00\xd8\x00', 4),
            ("utf-8", "\udfff", b'\xed\xbf\xbf', 3),
            ("utf-16le", "\udfff", b'\xff\xdf', 2),
            ("utf-16be", "\udfff", b'\xdf\xff', 2),
            ("utf-32le", "\udfff", b'\xff\xdf\x00\x00', 4),
            ("utf-32be", "\udfff", b'\x00\x00\xdf\xff', 4),
            ("utf-8", "\ud800\udfff", b'\xed\xa0\x80\xed\xbf\xbf', 3),
            ("utf-16le", "\ud800\udfff", b'\x00\xd8\xff\xdf', 2),
            ("utf-16be", "\ud800\udfff", b'\xd8\x00\xdf\xff', 2),
            ("utf-32le", "\ud800\udfff", b'\x00\xd8\x00\x00\xff\xdf\x00\x00', 4),
            ("utf-32be", "\ud800\udfff", b'\x00\x00\xd8\x00\x00\x00\xdf\xff', 4),
        ]
        for enc, s, b, n in tests:
            assert surrogatepass_errors(
                UnicodeEncodeError(enc, "a" + s + "b", 1, 1 + len(s), "ouch")
            ) == (b, 1 + len(s))
            assert surrogatepass_errors(
                UnicodeDecodeError(enc, bytearray(b"a" + b[:n] + b"b"),
                                   1, 1 + n, "ouch")
            ) == (s[:1], 1 + n)

    def test_badhandler(self):
        import codecs
        results = ( 42, u"foo", (1,2,3), (u"foo", 1, 3), (u"foo", None), (u"foo",), ("foo", 1, 3), ("foo", None), ("foo",) )
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
        codecs.register_error(errors, lambda x: (u'', sys.maxsize + 1))
        # CPython raises OverflowError here
        raises((IndexError, OverflowError), b'apple\x92ham\x93spam'.decode, 'utf-8', errors)

    def test_badhandler_returns_unicode(self):
        import codecs
        import sys
        errors = 'test.badhandler_unicode'
        codecs.register_error(errors, lambda x: (chr(100000), x.end))
        # CPython raises OverflowError here
        raises(UnicodeEncodeError, u'\udc80\ud800\udfff'.encode, 'utf-8', errors)

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

        res = b"\x00\x00\x00\x00\x00".decode("unicode-internal", "ignore")
        if sys.maxunicode > 65535:
            assert res == u"\u0000"   # UCS4 build
        else:
            assert res == u"\x00\x00" # UCS2 build

        def handler_unicodeinternal(exc):
            if not isinstance(exc, UnicodeDecodeError):
                raise TypeError("don't know how to handle %r" % exc)
            return (u"\x01", 1)
        codecs.register_error("test.hui", handler_unicodeinternal)
        res = b"\x00\x00\x00\x00\x00".decode("unicode-internal", "test.hui")
        if sys.maxunicode > 65535:
            assert res == u"\u0000\u0001\u0000"   # UCS4 build
        else:
            assert res == u"\x00\x00\x01" # UCS2 build

        def handler1(exc):
            if not isinstance(exc, UnicodeEncodeError) \
               and not isinstance(exc, UnicodeDecodeError):
                raise TypeError("don't know how to handle %r" % exc)
            l = [u"<%d>" % exc.object[pos] for pos in range(exc.start, exc.end)]
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
            b"\x00\x00\x00\x00\x00".decode("unicode-internal", "test.inf")
        except MyException:
            pass
        else:
            raise AssertionError("should have gone into infinite loop")

    def test_encode_error_bad_handler(self):
        import codecs
        codecs.register_error("test.bad_handler", lambda e: (repl, 1))
        assert u"xyz".encode("latin-1", "test.bad_handler") == b"xyz"
        repl = u"\u1234"
        raises(UnicodeEncodeError, u"\u5678".encode, "latin-1",
               "test.bad_handler")
        repl = u"\u00E9"
        s = u"\u5678".encode("latin-1", "test.bad_handler")
        assert s == b'\xe9'
        raises(UnicodeEncodeError, "\u5678".encode, "ascii",
               "test.bad_handler")

    def test_lone_surrogates(self):
        encodings = ('utf-8', 'utf-16', 'utf-16-le', 'utf-16-be',
            'utf-32', 'utf-32-le', 'utf-32-be')
        for encoding in encodings:
            raises(UnicodeEncodeError, u'\ud800'.encode, encoding)
            assert (u'[\udc80]'.encode(encoding, "backslashreplace") ==
                '[\\udc80]'.encode(encoding))
            assert (u'[\udc80]'.encode(encoding, "ignore") ==
                '[]'.encode(encoding))
            assert (u'[\udc80]'.encode(encoding, "replace") ==
                '[?]'.encode(encoding))
            # surrogate sequences
            assert (u'[\ud800\udc80]'.encode(encoding, "ignore") ==
                '[]'.encode(encoding))
            assert (u'[\ud800\udc80]'.encode(encoding, "replace") ==
                '[??]'.encode(encoding))
        for encoding, ill_surrogate in [('utf-8', b'\xed\xb2\x80'),
                                        ('utf-16-le', b'\x80\xdc'),
                                        ('utf-16-be', b'\xdc\x80'),
                                        ('utf-32-le', b'\x80\xdc\x00\x00'),
                                        ('utf-32-be', b'\x00\x00\xdc\x80')]:
            ill_formed_sequence_replace = "\ufffd"
            if encoding == 'utf-8':
                ill_formed_sequence_replace *= 3
            bom = "".encode(encoding)
            for before, after in [("\U00010fff", "A"), ("[", "]"),
                              ("A", "\U00010fff")]:
                before_sequence = before.encode(encoding)[len(bom):]
                after_sequence = after.encode(encoding)[len(bom):]
                test_string = before + "\uDC80" + after
                test_sequence = (bom + before_sequence + ill_surrogate + after_sequence)
                raises(UnicodeDecodeError, test_sequence.decode, encoding)
                assert test_string.encode(encoding, 'surrogatepass') == test_sequence
                assert test_sequence.decode(encoding, 'surrogatepass') == test_string
                assert test_sequence.decode(encoding, 'ignore') == before + after
                assert test_sequence.decode(encoding, 'replace') == (before +
                                                ill_formed_sequence_replace + after), str(
                (encoding, test_sequence, before + ill_formed_sequence_replace + after))
                backslashreplace = ''.join('\\x%02x' % b for b in ill_surrogate)
                assert test_sequence.decode(encoding, "backslashreplace") == (before +
                                                             backslashreplace + after)

    def test_lone_surrogates_utf_8(self):
        """
        utf-8 should not longer allow surrogates,
        and should return back full surrogate pairs.
        """
        e = raises(UnicodeEncodeError, u"\udc80\ud800\udfff".encode, "utf-8",
                   "surrogateescape").value
        assert e.start == 1
        assert e.end == 3
        assert e.object[e.start:e.end] == u'\ud800\udfff'

    def test_charmap_encode(self):
        assert 'xxx'.encode('charmap') == b'xxx'

        import codecs
        exc = raises(TypeError, codecs.charmap_encode, u'\xff', "replace",  {0xff: 300})
        assert str(exc.value) == 'character mapping must be in range(256)'
        exc = raises(TypeError, codecs.charmap_encode, u'\xff', "replace",  {0xff: u'a'})
        assert str(exc.value) == 'character mapping must return integer, bytes or None, not str'
        raises(UnicodeError, codecs.charmap_encode, u"\xff", "replace", {0xff: None})

    def test_charmap_encode_replace(self):
        charmap = dict([(c, bytes([c, c]).upper()) for c in b"abcdefgh"])
        charmap[ord("?")] = b"XYZ"
        import codecs
        sin = u"abcDEF"
        sout = codecs.charmap_encode(sin, "replace", charmap)[0]
        assert sout == b"AABBCCXYZXYZXYZ"

    def test_charmap_decode_2(self):
        assert b'foo'.decode('charmap') == 'foo'

    def test_charmap_build(self):
        import codecs
        assert codecs.charmap_build(u'123456') == {49: 0, 50: 1, 51: 2,
                                                   52: 3, 53: 4, 54: 5}

    def test_utf7_start_end_in_exception(self):
        try:
            b'+IC'.decode('utf-7')
        except UnicodeDecodeError as exc:
            assert exc.start == 0
            assert exc.end == 3

    def test_utf7_surrogate(self):
        assert b'+3ADYAA-'.decode('utf-7') == u'\udc00\ud800'

    def test_utf_7_decode(self):
        from _codecs import utf_7_decode
        res = utf_7_decode(b'+')
        assert res == (u'', 0)

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
        import _codecs
        assert u'\\'.encode('unicode-escape') == b'\\\\'
        assert b'\\\\'.decode('unicode-escape') == u'\\'
        assert u'\ud801'.encode('unicode-escape') == b'\\ud801'
        assert u'\u0013'.encode('unicode-escape') == b'\\x13'
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
        raises(UnicodeEncodeError, u'\u040a'.encode, 'mbcs')
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
            decoder(encoded_abc)
            assert len(w) == 1
            assert str(w[0].message) == warning_msg
            assert w[0].category == DeprecationWarning

    def test_xmlcharrefreplace(self):
        r = u'\u1234\u0080\u2345\u0079\u00AB'.encode('latin1', 'xmlcharrefreplace')
        assert r == b'&#4660;\x80&#9029;y\xab'
        r = u'\u1234\u0080\u2345\u0079\u00AB'.encode('ascii', 'xmlcharrefreplace')
        assert r == b'&#4660;&#128;&#9029;y&#171;'

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
        assert sin.encode("ascii", "test.record") == b""
        assert errors == [sin]

        errors = []
        assert sin.encode("latin-1", "test.record") == b"\xac"
        assert errors == [u'\u1234\u1234\u20ac\u8000']

        errors = []
        assert sin.encode("iso-8859-15", "test.record") == b"\xac\xa4"
        assert errors == [u'\u1234\u1234', u'\u8000']

    def test_unmapped(self):
        # from stdlib tests, bad byte: \xa5 is unmapped in iso-8859-3
        assert (b"foo\xa5bar".decode("iso-8859-3", "surrogateescape") ==
                     "foo\udca5bar")
        assert ("foo\udca5bar".encode("iso-8859-3", "surrogateescape") ==
                         b"foo\xa5bar")

    def test_warn_escape_decode(self):
        import warnings
        import codecs

        with warnings.catch_warnings(record=True) as l:
            warnings.simplefilter("always")
            codecs.unicode_escape_decode(b'\\A')
            codecs.unicode_escape_decode(b"\\" + b"\xff")

        assert len(l) == 2
        assert isinstance(l[0].message, DeprecationWarning)
        assert isinstance(l[1].message, DeprecationWarning)

    def test_invalid_type_errors(self):
        # hex is not a text encoding. it works via the codecs functions, but
        # not the methods
        if not self.appdirect:
            skip('"hex" only available after translation')
        import codecs
        res = codecs.decode(b"aabb", "hex")
        assert res == b"\xaa\xbb"
        res = codecs.decode(u"aabb", "hex")
        assert res == b"\xaa\xbb"
        res = codecs.encode(b"\xaa\xbb", "hex")
        assert res == b"aabb"

        raises(LookupError, u"abc".encode, "hex")

    def test_non_text_codec(self):
        import _codecs
        def search_function(encoding):
            def f(input, errors="strict"):
                return 52, len(input)
            if encoding == 'test.mynontextenc':
                return (f, f, None, None)
            return None
        _codecs.register(search_function)
        res = _codecs.encode(u"abc", "test.mynontextenc")
        assert res == 52
        res = _codecs.decode(b"abc", "test.mynontextenc")
        assert res == 52
        raises(TypeError, u"abc".encode, "test.mynontextenc")
        raises(TypeError, b"abc".decode, "test.mynontextenc")
