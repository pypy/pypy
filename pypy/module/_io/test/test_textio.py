class AppTestTextIO:
    spaceconfig = dict(usemodules=['_io', '_locale', 'array'])

    def setup_class(cls):
        from rpython.rlib.rarithmetic import INT_MAX, UINT_MAX
        space = cls.space
        cls.w_INT_MAX = space.wrap(INT_MAX)
        cls.w_UINT_MAX = space.wrap(UINT_MAX)

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
        assert t.readline() == "\xe9\n"
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
        #
        class CustomFile(object):
            def isatty(self): return 'YES'
            readable = writable = seekable = lambda self: False
        t = _io.TextIOWrapper(CustomFile())
        assert t.isatty() == 'YES'

    def test_default_implementations(self):
        import _io
        file = _io._TextIOBase()
        raises(_io.UnsupportedOperation, file.read)
        raises(_io.UnsupportedOperation, file.seek, 0)
        raises(_io.UnsupportedOperation, file.readline)
        raises(_io.UnsupportedOperation, file.detach)

    def test_isatty(self):
        import _io
        class Tty(_io.BytesIO):
            def isatty(self):
                return True
        txt = _io.TextIOWrapper(Tty())
        assert txt.isatty()

    def test_unreadable(self):
        import _io
        class UnReadable(_io.BytesIO):
            def readable(self):
                return False
        txt = _io.TextIOWrapper(UnReadable())
        raises(IOError, txt.read)

    def test_unwritable(self):
        import _io
        class UnWritable(_io.BytesIO):
            def writable(self):
                return False
        txt = _io.TextIOWrapper(UnWritable())
        raises(_io.UnsupportedOperation, txt.write, "blah")
        raises(_io.UnsupportedOperation, txt.writelines, ["blah\n"])

    def test_invalid_seek(self):
        import _io
        t = _io.TextIOWrapper(_io.BytesIO(b"\xc3\xa9\n\n"))
        raises(_io.UnsupportedOperation, t.seek, 1, 1)
        raises(_io.UnsupportedOperation, t.seek, 1, 2)

    def test_unseekable(self):
        import _io
        class Unseekable(_io.BytesIO):
            def seekable(self):
                return False
        txt = _io.TextIOWrapper(Unseekable())
        raises(_io.UnsupportedOperation, txt.tell)
        raises(_io.UnsupportedOperation, txt.seek, 0)

    def test_detach(self):
        import _io
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

    def test_newlinetranslate(self):
        import _io
        r = _io.BytesIO(b"abc\r\ndef\rg")
        b = _io.BufferedReader(r, 1000)
        t = _io.TextIOWrapper(b)
        assert t.read() == "abc\ndef\ng"

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
        assert ''.join(reads) == "abc\ndef\ng"

    def test_read_some_then_all(self):
        import _io
        r = _io.BytesIO(b"abc\ndef\n")
        t = _io.TextIOWrapper(r)
        reads = t.read(4)
        reads += t.read()
        assert reads == "abc\ndef\n"

    def test_read_some_then_readline(self):
        import _io
        r = _io.BytesIO(b"abc\ndef\n")
        t = _io.TextIOWrapper(r)
        reads = t.read(4)
        reads += t.readline()
        assert reads == "abc\ndef\n"

    def test_encoded_writes(self):
        import _io
        data = "1234567890"
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

    def test_writelines_error(self):
        import _io
        txt = _io.TextIOWrapper(_io.BytesIO())
        raises(TypeError, txt.writelines, [1, 2, 3])
        raises(TypeError, txt.writelines, None)
        raises(TypeError, txt.writelines, b'abc')

    def test_tell(self):
        import _io
        r = _io.BytesIO(b"abc\ndef\n")
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
        t.write("abc")
        del t
        import gc; gc.collect()
        assert l == [b"abc"]

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

        s = b"AAA\r\nBBB\rCCC\r\nDDD\nEEE\r\n"
        r = "AAA\nBBB\nCCC\nDDD\nEEE\n"
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

        t = _io.TextIOWrapper(_io.BytesIO(b""))
        # CPython raises an AttributeError, we raise a TypeError.
        raises((AttributeError, TypeError), setattr, t, "name", "anything")

    def test_repr(self):
        import _io

        t = _io.TextIOWrapper(_io.BytesIO(b""), encoding="utf-8")
        assert repr(t) == "<_io.TextIOWrapper encoding='utf-8'>"
        t = _io.TextIOWrapper(_io.BytesIO(b""), encoding="ascii")
        assert repr(t) == "<_io.TextIOWrapper encoding='ascii'>"
        t = _io.TextIOWrapper(_io.BytesIO(b""), encoding="utf-8")
        assert repr(t) == "<_io.TextIOWrapper encoding='utf-8'>"
        b = _io.BytesIO(b"")
        t = _io.TextIOWrapper(b, encoding="utf-8")
        b.name = "dummy"
        assert repr(t) == "<_io.TextIOWrapper name='dummy' encoding='utf-8'>"
        t.mode = "r"
        assert repr(t) == "<_io.TextIOWrapper name='dummy' mode='r' encoding='utf-8'>"
        b.name = b"dummy"
        assert repr(t) == "<_io.TextIOWrapper name=b'dummy' mode='r' encoding='utf-8'>"

    def test_rawio(self):
        # Issue #12591: TextIOWrapper must work with raw I/O objects, so
        # that subprocess.Popen() can have the required unbuffered
        # semantics with universal_newlines=True.
        import _io
        raw = self.get_MockRawIO()([b'abc', b'def', b'ghi\njkl\nopq\n'])
        txt = _io.TextIOWrapper(raw, encoding='ascii', newline='\n')
        # Reads
        assert txt.read(4) == 'abcd'
        assert txt.readline() == 'efghi\n'
        assert list(txt) == ['jkl\n', 'opq\n']

    def test_rawio_write_through(self):
        # Issue #12591: with write_through=True, writes don't need a flush
        import _io
        raw = self.get_MockRawIO()([b'abc', b'def', b'ghi\njkl\nopq\n'])
        txt = _io.TextIOWrapper(raw, encoding='ascii', newline='\n',
                                write_through=True)
        txt.write('1')
        txt.write('23\n4')
        txt.write('5')
        assert b''.join(raw._write_stack) == b'123\n45'

    def w_get_MockRawIO(self):
        import _io
        class MockRawIO(_io._RawIOBase):
            def __init__(self, read_stack=()):
                self._read_stack = list(read_stack)
                self._write_stack = []
                self._reads = 0
                self._extraneous_reads = 0

            def write(self, b):
                self._write_stack.append(bytes(b))
                return len(b)

            def writable(self):
                return True

            def fileno(self):
                return 42

            def readable(self):
                return True

            def seekable(self):
                return True

            def seek(self, pos, whence):
                return 0   # wrong but we gotta return something

            def tell(self):
                return 0   # same comment as above

            def readinto(self, buf):
                self._reads += 1
                max_len = len(buf)
                try:
                    data = self._read_stack[0]
                except IndexError:
                    self._extraneous_reads += 1
                    return 0
                if data is None:
                    del self._read_stack[0]
                    return None
                n = len(data)
                if len(data) <= max_len:
                    del self._read_stack[0]
                    buf[:n] = data
                    return n
                else:
                    buf[:] = data[:max_len]
                    self._read_stack[0] = data[max_len:]
                    return max_len

            def truncate(self, pos=None):
                return pos

            def read(self, n=None):
                self._reads += 1
                try:
                    return self._read_stack.pop(0)
                except:
                    self._extraneous_reads += 1
                    return b""
        return MockRawIO

    def test_flush_error_on_close(self):
        import _io
        txt = _io.TextIOWrapper(_io.BytesIO(b""), encoding="ascii")
        def bad_flush():
            raise IOError()
        txt.flush = bad_flush
        raises(IOError, txt.close)  # exception not swallowed
        assert txt.closed

    def test_close_error_on_close(self):
        import _io as io
        buffer = io.BytesIO(b'testdata')
        def bad_flush():
            raise OSError('flush')
        def bad_close():
            raise OSError('close')
        buffer.close = bad_close
        txt = io.TextIOWrapper(buffer, encoding="ascii")
        txt.flush = bad_flush
        err = raises(OSError, txt.close)
        assert err.value.args == ('close',)
        assert isinstance(err.value.__context__, OSError)
        assert err.value.__context__.args == ('flush',)
        assert not txt.closed

    def test_illegal_decoder(self):
        import _io
        raises(LookupError, _io.TextIOWrapper, _io.BytesIO(),
               encoding='quopri_codec')

    def test_read_nonbytes(self):
        import _io
        class NonbytesStream(_io.StringIO):
            read1 = _io.StringIO.read
        t = _io.TextIOWrapper(NonbytesStream(u'a'))
        raises(TypeError, t.read, 1)
        t = _io.TextIOWrapper(NonbytesStream(u'a'))
        raises(TypeError, t.readline)
        t = _io.TextIOWrapper(NonbytesStream(u'a'))
        raises(TypeError, t.read)

    def test_read_byteslike(self):
        import _io as io
        import array

        class MemviewBytesIO(io.BytesIO):
            '''A BytesIO object whose read method returns memoryviews
               rather than bytes'''

            def read1(self, len_):
                return _to_memoryview(super().read1(len_))

            def read(self, len_):
                return _to_memoryview(super().read(len_))

        def _to_memoryview(buf):
            '''Convert bytes-object *buf* to a non-trivial memoryview'''

            arr = array.array('i')
            idx = len(buf) - len(buf) % arr.itemsize
            arr.frombytes(buf[:idx])
            return memoryview(arr)

        r = MemviewBytesIO(b'Just some random string\n')
        t = io.TextIOWrapper(r, 'utf-8')

        # TextIOwrapper will not read the full string, because
        # we truncate it to a multiple of the native int size
        # so that we can construct a more complex memoryview.
        bytes_val =  _to_memoryview(r.getvalue()).tobytes()

        assert t.read(200) == bytes_val.decode('utf-8')

    def test_device_encoding(self):
        import os
        import sys
        encoding = os.device_encoding(sys.stderr.fileno())
        if not encoding:
            skip("Requires a result from "
                 "os.device_encoding(sys.stderr.fileno())")
        import _io
        f = _io.TextIOWrapper(sys.stderr.buffer)
        assert f.encoding == encoding

    def test_device_encoding_ovf(self):
        import _io
        b = _io.BytesIO()
        b.fileno = lambda: self.INT_MAX + 1
        raises(OverflowError, _io.TextIOWrapper, b)
        b.fileno = lambda: self.UINT_MAX + 1
        raises(OverflowError, _io.TextIOWrapper, b)

    def test_uninitialized(self):
        import _io
        t = _io.TextIOWrapper.__new__(_io.TextIOWrapper)
        del t
        t = _io.TextIOWrapper.__new__(_io.TextIOWrapper)
        raises(Exception, repr, t)
        raises(ValueError, t.read, 0)
        t.__init__(_io.BytesIO())
        assert t.read(0) == u''


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

            _check_decode(b'\xe8\xa2\x88', "\u8888")

            _check_decode(b'\xe8', "")
            _check_decode(b'\xa2', "")
            _check_decode(b'\x88', "\u8888")

            _check_decode(b'\xe8', "")
            _check_decode(b'\xa2', "")
            _check_decode(b'\x88', "\u8888")

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

            _check_decode(b'\xe8\xa2\x88\r\n', "\u8888\n")
            _check_decode(b'\xe8\xa2\x88', "\u8888")
            _check_decode(b'\n', "\n")
            _check_decode(b'\xe8\xa2\x88\r', "\u8888")
            _check_decode(b'\n', "\n")

        def check_newline_decoding(decoder, encoding):
            result = []
            if encoding is not None:
                encoder = codecs.getincrementalencoder(encoding)()
                def _decode_bytewise(s):
                    # Decode one byte at a time
                    for b in encoder.encode(s):
                        result.append(decoder.decode(bytes([b])))
            else:
                encoder = None
                def _decode_bytewise(s):
                    # Decode one char at a time
                    for c in s:
                        result.append(decoder.decode(c))
            assert decoder.newlines == None
            _decode_bytewise("abc\n\r")
            assert decoder.newlines == '\n'
            _decode_bytewise("\nabc")
            assert decoder.newlines == ('\n', '\r\n')
            _decode_bytewise("abc\r")
            assert decoder.newlines == ('\n', '\r\n')
            _decode_bytewise("abc")
            assert decoder.newlines == ('\r', '\n', '\r\n')
            _decode_bytewise("abc\r")
            assert "".join(result) == "abc\n\nabcabc\nabcabc"
            decoder.reset()
            input = "abc"
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
            assert dec.decode("\u0D00") == "\u0D00"
            assert dec.newlines is None
            assert dec.decode("\u0A00") == "\u0A00"
            assert dec.newlines is None
        dec = _io.IncrementalNewlineDecoder(None, translate=False)
        _check(dec)
        dec = _io.IncrementalNewlineDecoder(None, translate=True)
        _check(dec)
