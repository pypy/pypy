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

class AppTestOpen:
    def setup_class(cls):
        tmpfile = udir.join('tmpfile').ensure()
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def test_open(self):
        import io
        f = io.open(self.tmpfile, "rb")
        assert f.name.endswith('tmpfile')
        assert f.mode == 'rb'
        f.close()

    def test_open_writable(self):
        import io
        f = io.open(self.tmpfile, "w+b")
        f.close()

