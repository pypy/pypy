#encoding: utf-8
# spaceconfig = {"usemodules": ["_locale"]}
import _io

def test_constructor():
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

def test_properties():
    r = _io.BytesIO(b"\xc3\xa9\n\n")
    b = _io.BufferedReader(r, 1000)
    t = _io.TextIOWrapper(b)
    assert t.readable()
    assert t.seekable()
    #
    class CustomFile(object):
        def isatty(self): return 'YES'
        readable = writable = seekable = lambda self: False
    t = _io.TextIOWrapper(CustomFile())
    assert t.isatty() == 'YES'

def test_default_implementations():
    file = _io._TextIOBase()
    raises(_io.UnsupportedOperation, file.read)
    raises(_io.UnsupportedOperation, file.seek, 0)
    raises(_io.UnsupportedOperation, file.readline)
    raises(_io.UnsupportedOperation, file.detach)

def test_unreadable():
    class UnReadable(_io.BytesIO):
        def readable(self):
            return False
    txt = _io.TextIOWrapper(UnReadable())
    raises(IOError, txt.read)

def test_detach():
    b = _io.BytesIO()
    f = _io.TextIOWrapper(b)
    assert f.detach() is b
    raises(ValueError, f.fileno)
    raises(ValueError, f.close)
    raises(ValueError, f.detach)
    raises(ValueError, f.flush)

    # Operations independent of the detached stream should still work
    repr(f)
    assert isinstance(f.encoding, str)
    assert f.errors == "strict"
    assert not f.line_buffering

    assert not b.closed
    b.close()

def test_newlinetranslate():
    r = _io.BytesIO(b"abc\r\ndef\rg")
    b = _io.BufferedReader(r, 1000)
    t = _io.TextIOWrapper(b)
    assert t.read() == u"abc\ndef\ng"

def test_one_by_one():
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

def test_read_some_then_all():
    r = _io.BytesIO("abc\ndef\n")
    t = _io.TextIOWrapper(r)
    reads = t.read(4)
    reads += t.read()
    assert reads == u"abc\ndef\n"

def test_read_some_then_readline():
    r = _io.BytesIO("abc\ndef\n")
    t = _io.TextIOWrapper(r)
    reads = t.read(4)
    reads += t.readline()
    assert reads == u"abc\ndef\n"

def test_read_bug_unicode():
    inp = b"\xc3\xa4bc\ndef\n"
    r = _io.BytesIO(inp)
    t = _io.TextIOWrapper(r, encoding="utf-8")
    reads = t.read(4)
    assert reads == inp[:5].decode("utf-8")
    reads += t.readline()
    assert reads == inp.decode("utf-8")

def test_encoded_writes():
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

def test_writelines_error():
    txt = _io.TextIOWrapper(_io.BytesIO())
    raises(TypeError, txt.writelines, [1, 2, 3])
    raises(TypeError, txt.writelines, None)
    raises(TypeError, txt.writelines, b'abc')

def test_tell():
    r = _io.BytesIO("abc\ndef\n")
    t = _io.TextIOWrapper(r)
    assert t.tell() == 0
    t.read(4)
    assert t.tell() == 4

def test_destructor():
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

def test_newlines():
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

def test_readline():
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

def test_name():
    t = _io.TextIOWrapper(_io.BytesIO(""))
    # CPython raises an AttributeError, we raise a TypeError.
    raises((AttributeError, TypeError), setattr, t, "name", "anything")

def test_repr():
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

def test_flush_error_on_close():
    txt = _io.TextIOWrapper(_io.BytesIO(b""), encoding="ascii")
    def bad_flush():
        raise IOError()
    txt.flush = bad_flush
    raises(IOError, txt.close)  # exception not swallowed
    assert txt.closed

def test_illegal_encoder():
    # bpo-31271: A TypeError should be raised in case the return value of
    # encoder's encode() is invalid.
    class BadEncoder:
        def encode(self, dummy):
            return u'spam'
    def get_bad_encoder(dummy):
        return BadEncoder()
    import codecs
    rot13 = codecs.lookup("rot13")
    text_encoding = rot13._is_text_encoding
    incrementalencoder = rot13.incrementalencoder
    rot13._is_text_encoding = True
    rot13.incrementalencoder = get_bad_encoder
    try:
        t = _io.TextIOWrapper(_io.BytesIO(b'foo'), encoding="rot13")
    finally:
        rot13._is_text_encoding = text_encoding
        rot13.incrementalencoder = incrementalencoder
    with raises(TypeError):
        t.write(u'bar')
        t.flush()

def test_illegal_decoder():
    t = _io.TextIOWrapper(_io.BytesIO(b'aaaaaa'), newline='\n',
                         encoding='quopri_codec')
    raises(TypeError, t.read, 1)
    t = _io.TextIOWrapper(_io.BytesIO(b'aaaaaa'), newline='\n',
                         encoding='quopri_codec')
    raises(TypeError, t.readline)
    t = _io.TextIOWrapper(_io.BytesIO(b'aaaaaa'), newline='\n',
                         encoding='quopri_codec')
    raises(TypeError, t.read)

def test_read_nonbytes():
    class NonbytesStream(_io.StringIO):
        read1 = _io.StringIO.read
    t = _io.TextIOWrapper(NonbytesStream(u'a'))
    raises(TypeError, t.read, 1)
    t = _io.TextIOWrapper(NonbytesStream(u'a'))
    raises(TypeError, t.readline)
    t = _io.TextIOWrapper(NonbytesStream(u'a'))
    t.read() == u'a'

def test_uninitialized():
    t = _io.TextIOWrapper.__new__(_io.TextIOWrapper)
    del t
    t = _io.TextIOWrapper.__new__(_io.TextIOWrapper)
    raises(Exception, repr, t)
    raises(ValueError, t.read, 0)
    t.__init__(_io.BytesIO())
    assert t.read(0) == u''

def test_issue25862():
    # CPython issue #25862
    # Assertion failures occurred in tell() after read() and write().
    from _io import TextIOWrapper, BytesIO
    t = TextIOWrapper(BytesIO(b'test'), encoding='ascii')
    t.read(1)
    t.read()
    t.tell()
    t = TextIOWrapper(BytesIO(b'test'), encoding='ascii')
    t.read(1)
    t.write(u'x')
    t.tell()

def test_newline_decoder():
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

def test_newline_bytes():
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

def test_newlines2():
    import codecs
    inner_decoder = codecs.getincrementaldecoder("utf-8")()
    decoder = _io.IncrementalNewlineDecoder(inner_decoder, translate=True)
    msg = b"abc\r\n\n\r\r\n\n"
    decoded = ''
    for ch in msg:
        decoded += decoder.decode(ch)
    assert set(decoder.newlines) == {"\r", "\n", "\r\n"}
