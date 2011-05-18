from __future__ import with_statement

from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir


class AppTestIoModule:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])

    def test_import(self):
        import io

    def test_iobase(self):
        import io
        io.IOBase()

        class MyFile(io.BufferedIOBase):
            def __init__(self, filename):
                pass
        MyFile("file")

    def test_openclose(self):
        import io
        with io.BufferedIOBase() as f:
            assert not f.closed
        assert f.closed

    def test_iter(self):
        import io
        class MyFile(io.IOBase):
            def __init__(self):
                self.lineno = 0
            def readline(self):
                self.lineno += 1
                if self.lineno == 1:
                    return "line1"
                elif self.lineno == 2:
                    return "line2"
                return ""

        assert list(MyFile()) == ["line1", "line2"]

    def test_exception(self):
        import _io
        e = _io.UnsupportedOperation("seek")

    def test_blockingerror(self):
        import _io
        try:
            raise _io.BlockingIOError(42, "test blocking", 123)
        except IOError, e:
            assert isinstance(e, _io.BlockingIOError)
            assert e.errno == 42
            assert e.strerror == "test blocking"
            assert e.characters_written == 123

    def test_dict(self):
        import _io
        f = _io.BytesIO()
        f.x = 42
        assert f.x == 42
        #
        def write(data):
            try:
                data = data.tobytes().upper()
            except AttributeError:
                data = data.upper()
            return _io.BytesIO.write(f, data)
        f.write = write
        bufio = _io.BufferedWriter(f)
        bufio.write("abc")
        bufio.flush()
        assert f.getvalue() == "ABC"

    def test_destructor(self):
        import io
        io.IOBase()

        record = []
        class MyIO(io.IOBase):
            def __del__(self):
                record.append(1)
                super(MyIO, self).__del__()
            def close(self):
                record.append(2)
                super(MyIO, self).close()
            def flush(self):
                record.append(3)
                super(MyIO, self).flush()
        MyIO()
        import gc; gc.collect()
        assert record == [1, 2, 3]

    def test_tell(self):
        import io
        class MyIO(io.IOBase):
            def seek(self, pos, whence=0):
                return 42
        assert MyIO().tell() == 42

    def test_weakref(self):
        import _io
        import weakref
        f = _io.BytesIO()
        ref = weakref.ref(f)
        assert ref() is f

    def test_rawio_read(self):
        import _io
        class MockRawIO(_io._RawIOBase):
            stack = ['abc', 'de', '']
            def readinto(self, buf):
                data = self.stack.pop(0)
                buf[:len(data)] = data
                return len(data)
        assert MockRawIO().read() == 'abcde'

    def test_rawio_read_pieces(self):
        import _io
        class MockRawIO(_io._RawIOBase):
            stack = ['abc', 'de', None, 'fg', '']
            def readinto(self, buf):
                data = self.stack.pop(0)
                if data is None:
                    return None
                if len(data) <= len(buf):
                    buf[:len(data)] = data
                    return len(data)
                else:
                    buf[:] = data[:len(buf)]
                    self.stack.insert(0, data[len(buf):])
                    return len(buf)
        r = MockRawIO()
        assert r.read(2) == 'ab'
        assert r.read(2) == 'c'
        assert r.read(2) == 'de'
        assert r.read(2) == None
        assert r.read(2) == 'fg'
        assert r.read(2) == ''

class AppTestOpen:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io', '_locale'])
        tmpfile = udir.join('tmpfile').ensure()
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def test_open(self):
        import io
        f = io.open(self.tmpfile, "rb")
        assert f.name.endswith('tmpfile')
        assert f.mode == 'rb'
        f.close()

        with io.open(self.tmpfile, "rt") as f:
            assert f.mode == "rt"

    def test_open_writable(self):
        import io
        f = io.open(self.tmpfile, "w+b")
        f.close()

    def test_valid_mode(self):
        import io

        raises(ValueError, io.open, self.tmpfile, "ww")
        raises(ValueError, io.open, self.tmpfile, "rwa")
        raises(ValueError, io.open, self.tmpfile, "b", newline="\n")

    def test_array_write(self):
        import _io, array
        a = array.array(b'i', range(10))
        n = len(a.tostring())
        with _io.open(self.tmpfile, "wb", 0) as f:
            res = f.write(a)
            assert res == n

        with _io.open(self.tmpfile, "wb") as f:
            res = f.write(a)
            assert res == n

    def test_attributes(self):
        import _io

        with _io.open(self.tmpfile, "wb", buffering=0) as f:
            assert f.mode == "wb"

        with _io.open(self.tmpfile, "U") as f:
            assert f.name == self.tmpfile
            assert f.buffer.name == self.tmpfile
            assert f.buffer.raw.name == self.tmpfile
            assert f.mode == "U"
            assert f.buffer.mode == "rb"
            assert f.buffer.raw.mode == "rb"

        with _io.open(self.tmpfile, "w+") as f:
            assert f.mode == "w+"
            assert f.buffer.mode == "rb+"
            assert f.buffer.raw.mode == "rb+"

            with _io.open(f.fileno(), "wb", closefd=False) as g:
                assert g.mode == "wb"
                assert g.raw.mode == "wb"
                assert g.name == f.fileno()
                assert g.raw.name == f.fileno()

    def test_seek_and_tell(self):
        import _io

        with _io.open(self.tmpfile, "wb") as f:
            f.write("abcd")

        with _io.open(self.tmpfile) as f:
            decoded = f.read()

        # seek positions
        for i in xrange(len(decoded) + 1):
            # read lenghts
            for j in [1, 5, len(decoded) - i]:
                with _io.open(self.tmpfile) as f:
                    res = f.read(i)
                    assert res == decoded[:i]
                    cookie = f.tell()
                    res = f.read(j)
                    assert res == decoded[i:i + j]
                    f.seek(cookie)
                    res = f.read()
                    assert res == decoded[i:]

    def test_telling(self):
        import _io

        with _io.open(self.tmpfile, "w+", encoding="utf8") as f:
            p0 = f.tell()
            f.write(u"\xff\n")
            p1 = f.tell()
            f.write(u"\xff\n")
            p2 = f.tell()
            f.seek(0)

            assert f.tell() == p0
            res = f.readline()
            assert res == u"\xff\n"
            assert f.tell() == p1
            res = f.readline()
            assert res == u"\xff\n"
            assert f.tell() == p2
            f.seek(0)

            for line in f:
                assert line == u"\xff\n"
                raises(IOError, f.tell)
            assert f.tell() == p2

    def test_chunk_size(self):
        import _io

        with _io.open(self.tmpfile) as f:
            assert f._CHUNK_SIZE >= 1
            f._CHUNK_SIZE = 4096
            assert f._CHUNK_SIZE == 4096
            raises(ValueError, setattr, f, "_CHUNK_SIZE", 0)

    def test_truncate(self):
        import _io

        with _io.open(self.tmpfile, "w+") as f:
            f.write(u"abc")

        with _io.open(self.tmpfile, "w+") as f:
            f.truncate()

        with _io.open(self.tmpfile, "r+") as f:
            res = f.read()
            assert res == ""

    def test_errors_property(self):
        import _io

        with _io.open(self.tmpfile, "w") as f:
            assert f.errors == "strict"
        with _io.open(self.tmpfile, "w", errors="replace") as f:
            assert f.errors == "replace"

    def test_append_bom(self):
        import _io

        # The BOM is not written again when appending to a non-empty file
        for charset in ["utf-8-sig", "utf-16", "utf-32"]:
            with _io.open(self.tmpfile, "w", encoding=charset) as f:
                f.write(u"aaa")
                pos = f.tell()
            with _io.open(self.tmpfile, "rb") as f:
                res = f.read()
                assert res == "aaa".encode(charset)
            with _io.open(self.tmpfile, "a", encoding=charset) as f:
                f.write(u"xxx")
            with _io.open(self.tmpfile, "rb") as f:
                res = f.read()
                assert res == "aaaxxx".encode(charset)

    def test_newlines_attr(self):
        import _io

        with _io.open(self.tmpfile, "r") as f:
            assert f.newlines is None

        with _io.open(self.tmpfile, "wb") as f:
            f.write("hello\nworld\n")

        with _io.open(self.tmpfile, "r") as f:
            res = f.readline()
            assert res == "hello\n"
            res = f.readline()
            assert res == "world\n"
            assert f.newlines == "\n"
            assert type(f.newlines) is unicode
