from pypy.conftest import gettestobjspace

class AppTestTextIO:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io', '_locale'])

    def test_constructor(self):
        import _io
        r = _io.BytesIO(b"\xc3\xa9\n\n")
        b = _io.BufferedReader(r, 1000)
        t = _io.TextIOWrapper(b)
        t.__init__(b, encoding="latin1", newline="\r\n")
        assert t.encoding == "latin1"
        assert t.line_buffering == False
        t.__init__(b, encoding="utf8", line_buffering=True)
        assert t.encoding == "utf8"
        assert t.line_buffering == True
        assert t.readline() == u"\xe9\n"
        raises(TypeError, t.__init__, b, newline=42)
        raises(ValueError, t.__init__, b, newline='xyzzy')
        t = _io.TextIOWrapper(b)
        assert t.encoding

    def test_properties(self):
        import _io
        r = _io.BytesIO(b"\xc3\xa9\n\n")
        b = _io.BufferedReader(r, 1000)
        t = _io.TextIOWrapper(b)
        assert t.readable()
        assert t.seekable()

    def test_unreadable(self):
        import _io
        class UnReadable(_io.BytesIO):
            def readable(self):
                return False
        txt = _io.TextIOWrapper(UnReadable())
        raises(IOError, txt.read)

    def test_detach(self):
        import _io
        b = _io.BytesIO()
        f = _io.TextIOWrapper(b)
        assert f.detach() is b
        raises(ValueError, f.fileno)
        raises(ValueError, f.close)
        raises(ValueError, f.detach)
        raises(ValueError, f.flush)
        assert not b.closed
        b.close()

    def test_newlinetranslate(self):
        import _io
        r = _io.BytesIO(b"abc\r\ndef\rg")
        b = _io.BufferedReader(r, 1000)
        t = _io.TextIOWrapper(b)
        assert t.read() == u"abc\ndef\ng"

    def test_one_by_one(self):
        import _io
        r = _io.BytesIO(b"abc\r\ndef\rg")
        t = _io.TextIOWrapper(r)
        reads = []
        while True:
            c = t.read(1)
            assert len(c) <= 1
            if not c:
                break
            reads.append(c)
        assert u''.join(reads) == u"abc\ndef\ng"

    def test_read_some_then_all(self):
        import _io
        r = _io.BytesIO("abc\ndef\n")
        t = _io.TextIOWrapper(r)
        reads = t.read(4)
        reads += t.read()
        assert reads == u"abc\ndef\n"

    def test_read_some_then_readline(self):
        import _io
        r = _io.BytesIO("abc\ndef\n")
        t = _io.TextIOWrapper(r)
        reads = t.read(4)
        reads += t.readline()
        assert reads == u"abc\ndef\n"

    def test_encoded_writes(self):
        import _io
        data = u"1234567890"
        tests = ("utf-16",
                 "utf-16-le",
                 "utf-16-be",
                 "utf-32",
                 "utf-32-le",
                 "utf-32-be")
        for encoding in tests:
            buf = _io.BytesIO()
            f = _io.TextIOWrapper(buf, encoding=encoding)
            # Check if the BOM is written only once (see issue1753).
            f.write(data)
            f.write(data)
            f.seek(0)
            assert f.read() == data * 2
            f.seek(0)
            assert f.read() == data * 2
            assert buf.getvalue() == (data * 2).encode(encoding)

    def test_tell(self):
        import _io
        r = _io.BytesIO("abc\ndef\n")
        t = _io.TextIOWrapper(r)
        assert t.tell() == 0
        t.read(4)
        assert t.tell() == 4

    def test_destructor(self):
        import _io
        l = []
        class MyBytesIO(_io.BytesIO):
            def close(self):
                l.append(self.getvalue())
                _io.BytesIO.close(self)
        b = MyBytesIO()
        t = _io.TextIOWrapper(b, encoding="ascii")
        t.write(u"abc")
        del t
        import gc; gc.collect()
        assert l == ["abc"]

    def test_newlines(self):
        import _io
        input_lines = [ "unix\n", "windows\r\n", "os9\r", "last\n", "nonl" ]

        tests = [
            [ None, [ 'unix\n', 'windows\n', 'os9\n', 'last\n', 'nonl' ] ],
            [ '', input_lines ],
            [ '\n', [ "unix\n", "windows\r\n", "os9\rlast\n", "nonl" ] ],
            [ '\r\n', [ "unix\nwindows\r\n", "os9\rlast\nnonl" ] ],
            [ '\r', [ "unix\nwindows\r", "\nos9\r", "last\nnonl" ] ],
        ]

        # Try a range of buffer sizes to test the case where \r is the last
        # character in TextIOWrapper._pending_line.
        encoding = "ascii"
        # XXX: str.encode() should return bytes
        data = bytes(''.join(input_lines).encode(encoding))
        for do_reads in (False, True):
            for bufsize in range(1, 10):
                for newline, exp_lines in tests:
                    bufio = _io.BufferedReader(_io.BytesIO(data), bufsize)
                    textio = _io.TextIOWrapper(bufio, newline=newline,
                                              encoding=encoding)
                    if do_reads:
                        got_lines = []
                        while True:
                            c2 = textio.read(2)
                            if c2 == '':
                                break
                            len(c2) == 2
                            got_lines.append(c2 + textio.readline())
                    else:
                        got_lines = list(textio)

                    for got_line, exp_line in zip(got_lines, exp_lines):
                        assert got_line == exp_line
                    assert len(got_lines) == len(exp_lines)

    def test_readline(self):
        import _io

        s = "AAA\r\nBBB\rCCC\r\nDDD\nEEE\r\n"
        r = "AAA\nBBB\nCCC\nDDD\nEEE\n".decode("ascii")
        txt = _io.TextIOWrapper(_io.BytesIO(s), encoding="ascii")
        txt._CHUNK_SIZE = 4

        reads = txt.read(4)
        reads += txt.read(4)
        reads += txt.readline()
        reads += txt.readline()
        reads += txt.readline()
        assert reads == r

    def test_name(self):
        import _io

        t = _io.TextIOWrapper(_io.BytesIO(""))
        # CPython raises an AttributeError, we raise a TypeError.
        raises((AttributeError, TypeError), setattr, t, "name", "anything")

    def test_repr(self):
        import _io

        t = _io.TextIOWrapper(_io.BytesIO(""), encoding="utf-8")
        assert repr(t) == "<_io.TextIOWrapper encoding='utf-8'>"
        t = _io.TextIOWrapper(_io.BytesIO(""), encoding="ascii")
        assert repr(t) == "<_io.TextIOWrapper encoding='ascii'>"
        t = _io.TextIOWrapper(_io.BytesIO(""), encoding=u"utf-8")
        assert repr(t) == "<_io.TextIOWrapper encoding='utf-8'>"
        b = _io.BytesIO("")
        t = _io.TextIOWrapper(b, encoding="utf-8")
        b.name = "dummy"
        assert repr(t) == "<_io.TextIOWrapper name='dummy' encoding='utf-8'>"


class AppTestIncrementalNewlineDecoder:

    def test_newline_decoder(self):
        import _io
        def check_newline_decoding_utf8(decoder):
            # UTF-8 specific tests for a newline decoder
            def _check_decode(b, s, **kwargs):
                # We exercise getstate() / setstate() as well as decode()
                state = decoder.getstate()
                assert decoder.decode(b, **kwargs) == s
                decoder.setstate(state)
                assert decoder.decode(b, **kwargs) == s

            _check_decode(b'\xe8\xa2\x88', u"\u8888")

            _check_decode(b'\xe8', "")
            _check_decode(b'\xa2', "")
            _check_decode(b'\x88', u"\u8888")

            _check_decode(b'\xe8', "")
            _check_decode(b'\xa2', "")
            _check_decode(b'\x88', u"\u8888")

            _check_decode(b'\xe8', "")
            raises(UnicodeDecodeError, decoder.decode, b'', final=True)

            decoder.reset()
            _check_decode(b'\n', "\n")
            _check_decode(b'\r', "")
            _check_decode(b'', "\n", final=True)
            _check_decode(b'\r', "\n", final=True)

            _check_decode(b'\r', "")
            _check_decode(b'a', "\na")

            _check_decode(b'\r\r\n', "\n\n")
            _check_decode(b'\r', "")
            _check_decode(b'\r', "\n")
            _check_decode(b'\na', "\na")

            _check_decode(b'\xe8\xa2\x88\r\n', u"\u8888\n")
            _check_decode(b'\xe8\xa2\x88', u"\u8888")
            _check_decode(b'\n', "\n")
            _check_decode(b'\xe8\xa2\x88\r', u"\u8888")
            _check_decode(b'\n', "\n")

        def check_newline_decoding(decoder, encoding):
            result = []
            if encoding is not None:
                encoder = codecs.getincrementalencoder(encoding)()
                def _decode_bytewise(s):
                    # Decode one byte at a time
                    for b in encoder.encode(s):
                        result.append(decoder.decode(b))
            else:
                encoder = None
                def _decode_bytewise(s):
                    # Decode one char at a time
                    for c in s:
                        result.append(decoder.decode(c))
            assert decoder.newlines == None
            _decode_bytewise(u"abc\n\r")
            assert decoder.newlines == '\n'
            _decode_bytewise(u"\nabc")
            assert decoder.newlines == ('\n', '\r\n')
            _decode_bytewise(u"abc\r")
            assert decoder.newlines == ('\n', '\r\n')
            _decode_bytewise(u"abc")
            assert decoder.newlines == ('\r', '\n', '\r\n')
            _decode_bytewise(u"abc\r")
            assert "".join(result) == "abc\n\nabcabc\nabcabc"
            decoder.reset()
            input = u"abc"
            if encoder is not None:
                encoder.reset()
                input = encoder.encode(input)
            assert decoder.decode(input) == "abc"
            assert decoder.newlines is None

        encodings = (
            # None meaning the IncrementalNewlineDecoder takes unicode input
            # rather than bytes input
            None, 'utf-8', 'latin-1',
            'utf-16', 'utf-16-le', 'utf-16-be',
            'utf-32', 'utf-32-le', 'utf-32-be',
        )
        import codecs
        for enc in encodings:
            decoder = enc and codecs.getincrementaldecoder(enc)()
            decoder = _io.IncrementalNewlineDecoder(decoder, translate=True)
            check_newline_decoding(decoder, enc)
        decoder = codecs.getincrementaldecoder("utf-8")()
        decoder = _io.IncrementalNewlineDecoder(decoder, translate=True)
        check_newline_decoding_utf8(decoder)

    def test_newline_bytes(self):
        import _io
        # Issue 5433: Excessive optimization in IncrementalNewlineDecoder
        def _check(dec):
            assert dec.newlines is None
            assert dec.decode(u"\u0D00") == u"\u0D00"
            assert dec.newlines is None
            assert dec.decode(u"\u0A00") == u"\u0A00"
            assert dec.newlines is None
        dec = _io.IncrementalNewlineDecoder(None, translate=False)
        _check(dec)
        dec = _io.IncrementalNewlineDecoder(None, translate=True)
        _check(dec)
