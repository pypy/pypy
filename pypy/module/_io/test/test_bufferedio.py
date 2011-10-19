from pypy.conftest import gettestobjspace, option
from pypy.interpreter.gateway import interp2app
from pypy.tool.udir import udir

class AppTestBufferedReader:
    spaceconfig = dict(usemodules=['_io'])

    def setup_class(cls):
        tmpfile = udir.join('tmpfile')
        tmpfile.write("a\nb\nc", mode='wb')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def test_simple_read(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.read() == b"a\nb\nc"
        raises(ValueError, f.read, -2)
        f.close()
        #
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        r = f.read(4)
        assert r == b"a\nb\n"
        f.close()

    def test_read_pieces(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.read(3) == b"a\nb"
        assert f.read(3) == b"\nc"
        assert f.read(3) == b""
        assert f.read(3) == b""
        f.close()

    def test_slow_provider(self):
        import _io
        class MockIO(_io._IOBase):
            def readable(self):
                return True
            def readinto(self, buf):
                buf[:3] = b"abc"
                return 3
        bufio = _io.BufferedReader(MockIO())
        r = bufio.read(5)
        assert r == b"abcab"

    def test_read_past_eof(self):
        import _io
        class MockIO(_io._IOBase):
            stack = [b"abc", b"d", b"efg"]
            def readable(self):
                return True
            def readinto(self, buf):
                if self.stack:
                    data = self.stack.pop(0)
                    buf[:len(data)] = data
                    return len(data)
                else:
                    return 0
        bufio = _io.BufferedReader(MockIO())
        assert bufio.read(9000) == b"abcdefg"

    def test_buffering(self):
        import _io
        data = b"abcdefghi"
        dlen = len(data)
        class MockFileIO(_io.BytesIO):
            def __init__(self, data):
                self.read_history = []
                _io.BytesIO.__init__(self, data)

            def read(self, n=None):
                res = _io.BytesIO.read(self, n)
                self.read_history.append(None if res is None else len(res))
                return res

            def readinto(self, b):
                res = _io.BytesIO.readinto(self, b)
                self.read_history.append(res)
                return res


        tests = [
            [ 100, [ 3, 1, 4, 8 ], [ dlen, 0 ] ],
            [ 100, [ 3, 3, 3],     [ dlen ]    ],
            [   4, [ 1, 2, 4, 2 ], [ 4, 4, 1 ] ],
        ]

        for bufsize, buf_read_sizes, raw_read_sizes in tests:
            rawio = MockFileIO(data)
            bufio = _io.BufferedReader(rawio, buffer_size=bufsize)
            pos = 0
            for nbytes in buf_read_sizes:
                assert bufio.read(nbytes) == data[pos:pos+nbytes]
                pos += nbytes
            # this is mildly implementation-dependent
            assert rawio.read_history == raw_read_sizes

    def test_peek(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.read(2) == b'a\n'
        assert f.peek().startswith(b'b\nc')
        assert f.read(3) == b'b\nc'
        assert f.peek() == b''

    def test_read1(self):
        import _io
        class RecordingFileIO(_io.FileIO):
            def read(self, size=-1):
                self.nbreads += 1
                return _io.FileIO.read(self, size)
            def readinto(self, buf):
                self.nbreads += 1
                return _io.FileIO.readinto(self, buf)
        raw = RecordingFileIO(self.tmpfile)
        raw.nbreads = 0
        f = _io.BufferedReader(raw, buffer_size=3)
        assert f.read(1) == b'a'
        assert f.read1(1) == b'\n'
        assert raw.nbreads == 1
        assert f.read1(100) == b'b'
        assert raw.nbreads == 1
        assert f.read1(100) == b'\nc'
        assert raw.nbreads == 2
        assert f.read1(100) == b''
        assert raw.nbreads == 3
        f.close()

    def test_readinto(self):
        import _io
        a = bytearray(b'x' * 10)
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.readinto(a) == 5
        f.close()
        assert a == b'a\nb\ncxxxxx'

    def test_seek(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.read() == b"a\nb\nc"
        f.seek(0)
        assert f.read() == b"a\nb\nc"
        f.seek(-2, 2)
        assert f.read() == b"\nc"
        f.close()

    def test_readlines(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.readlines() == [b'a\n', b'b\n', b'c']

    def test_detach(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.fileno() == raw.fileno()
        assert f.detach() is raw
        raises(ValueError, f.fileno)
        raises(ValueError, f.close)
        raises(ValueError, f.detach)
        raises(ValueError, f.flush)
        assert not raw.closed
        raw.close()

    def test_tell(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw, buffer_size=2)
        assert f.tell() == 0
        d1 = f.read(1)
        assert f.tell() == 1
        d2 = f.read(2)
        assert f.tell() == 3
        assert f.seek(0) == 0
        assert f.tell() == 0
        d3 = f.read(3)
        assert f.tell() == 3
        assert d1 + d2 == d3
        f.close()

    def test_repr(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert repr(f) == '<_io.BufferedReader name=%r>' % (self.tmpfile,)

class AppTestBufferedReaderWithThreads(AppTestBufferedReader):
    spaceconfig = dict(usemodules=['_io', 'thread'])


class AppTestBufferedWriter:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])
        tmpfile = udir.join('tmpfile')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))
        if option.runappdirect:
            cls.w_readfile = tmpfile.read
        else:
            def readfile(space):
                return space.wrapbytes(tmpfile.read())
            cls.w_readfile = cls.space.wrap(interp2app(readfile))

    def test_write(self):
        import _io
        raw = _io.FileIO(self.tmpfile, 'w')
        f = _io.BufferedWriter(raw)
        f.write(b"abcd")
        f.close()
        assert self.readfile() == b"abcd"

    def test_largewrite(self):
        import _io
        raw = _io.FileIO(self.tmpfile, 'w')
        f = _io.BufferedWriter(raw)
        f.write(b"abcd" * 5000)
        f.close()
        assert self.readfile() == b"abcd" * 5000

    def test_incomplete(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        b = _io.BufferedWriter.__new__(_io.BufferedWriter)
        raises(IOError, b.__init__, raw) # because file is not writable
        raises(ValueError, getattr, b, 'closed')
        raises(ValueError, b.flush)
        raises(ValueError, b.close)

    def test_deprecated_max_buffer_size(self):
        import _io, warnings
        raw = _io.FileIO(self.tmpfile, 'w')
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            f = _io.BufferedWriter(raw, max_buffer_size=8192)
        f.close()
        assert len(w) == 1
        assert str(w[0].message) == "max_buffer_size is deprecated"
        assert w[0].category is DeprecationWarning

    def test_check_several_writes(self):
        import _io
        raw = _io.FileIO(self.tmpfile, 'w')
        b = _io.BufferedWriter(raw, 13)

        for i in range(4):
            assert b.write(b'x' * 10) == 10
        b.flush()
        assert self.readfile() == b'x' * 40

    def test_destructor(self):
        import _io

        record = []
        class MyIO(_io.BufferedWriter):
            def __del__(self):
                record.append(1)
                super(MyIO, self).__del__()
            def close(self):
                record.append(2)
                super(MyIO, self).close()
            def flush(self):
                record.append(3)
                super(MyIO, self).flush()
        raw = _io.FileIO(self.tmpfile, 'w')
        MyIO(raw)
        import gc; gc.collect()
        assert record == [1, 2, 3]

    def test_truncate(self):
        import _io
        raw = _io.FileIO(self.tmpfile, 'w+')
        raw.write(b'x' * 20)
        b = _io.BufferedReader(raw)
        assert b.seek(8) == 8
        assert b.truncate() == 8
        assert b.tell() == 8

    def test_write_non_blocking(self):
        import _io, io
        class MockNonBlockWriterIO(io.RawIOBase):
            def __init__(self):
                self._write_stack = []
                self._blocker_char = None

            def writable(self):
                return True
            closed = False

            def pop_written(self):
                s = b''.join(self._write_stack)
                self._write_stack[:] = []
                return s

            def block_on(self, char):
                """Block when a given char is encountered."""
                self._blocker_char = char

            def write(self, b):
                try:
                    b = b.tobytes()
                except AttributeError:
                    pass
                n = -1
                if self._blocker_char:
                    try:
                        n = b.index(self._blocker_char)
                    except ValueError:
                        pass
                    else:
                        self._blocker_char = None
                        self._write_stack.append(b[:n])
                        raise _io.BlockingIOError(0, "test blocking", n)
                self._write_stack.append(b)
                return len(b)

        raw = MockNonBlockWriterIO()
        bufio = _io.BufferedWriter(raw, 8)

        assert bufio.write(b"abcd") == 4
        assert bufio.write(b"efghi") == 5
        # 1 byte will be written, the rest will be buffered
        raw.block_on(b"k")
        assert bufio.write(b"jklmn") == 5

        # 8 bytes will be written, 8 will be buffered and the rest will be lost
        raw.block_on(b"0")
        try:
            bufio.write(b"opqrwxyz0123456789")
        except _io.BlockingIOError as e:
            written = e.characters_written
        else:
            self.fail("BlockingIOError should have been raised")
        assert written == 16
        assert raw.pop_written() == b"abcdefghijklmnopqrwxyz"

        assert bufio.write(b"ABCDEFGHI") == 9
        s = raw.pop_written()
        # Previously buffered bytes were flushed
        assert s.startswith(b"01234567A")

    def test_read_non_blocking(self):
        import _io
        class MockRawIO(_io._RawIOBase):
            def __init__(self, read_stack=()):
                self._read_stack = list(read_stack)
            def readable(self):
                return True
            def readinto(self, buf):
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
            def read(self, n=None):
                try:
                    return self._read_stack.pop(0)
                except IndexError:
                    return b""
        # Inject some None's in there to simulate EWOULDBLOCK
        rawio = MockRawIO((b"abc", b"d", None, b"efg", None, None, None))
        bufio = _io.BufferedReader(rawio)

        assert bufio.read(6) == b"abcd"
        assert bufio.read(1) == b"e"
        assert bufio.read() == b"fg"
        assert bufio.peek(1) == b""
        assert bufio.read() is None
        assert bufio.read() == b""

class AppTestBufferedRWPair:
    def test_pair(self):
        import _io
        pair = _io.BufferedRWPair(_io.BytesIO(b"abc"), _io.BytesIO())
        assert not pair.closed
        assert pair.readable()
        assert pair.writable()
        assert not pair.isatty()
        assert pair.read() == b"abc"
        assert pair.write(b"abc") == 3

    def test_constructor_with_not_readable(self):
        import _io
        class NotReadable:
            def readable(self):
                return False

        raises(IOError, _io.BufferedRWPair, NotReadable(), _io.BytesIO())

    def test_constructor_with_not_writable(self):
        import _io
        class NotWritable:
            def writable(self):
                return False

        raises(IOError, _io.BufferedRWPair, _io.BytesIO(), NotWritable())

class AppTestBufferedRandom:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])
        tmpfile = udir.join('tmpfile')
        tmpfile.write(b"a\nb\nc", mode='wb')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def test_simple_read(self):
        import _io
        raw = _io.FileIO(self.tmpfile, 'rb+')
        f = _io.BufferedRandom(raw)
        assert f.read(3) == b'a\nb'
        f.write(b'xxxx')
        f.seek(0)
        assert f.read() == b'a\nbxxxx'
