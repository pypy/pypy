from pypy.conftest import gettestobjspace

class AppTestBytesIO:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])

    def test_init(self):
        import _io
        raises(TypeError, _io.BytesIO, u"12345")

    def test_init_kwargs(self):
        import _io

        buf = "1234567890"
        b = _io.BytesIO(initial_bytes=buf)
        assert b.read() == buf
        raises(TypeError, _io.BytesIO, buf, foo=None)

    def test_capabilities(self):
        import _io
        f = _io.BytesIO()
        assert f.readable()
        assert f.writable()
        assert f.seekable()
        f.close()

    def test_write(self):
        import _io
        f = _io.BytesIO()
        assert f.write("hello") == 5
        import gc; gc.collect()
        assert f.getvalue() == "hello"
        f.close()

    def test_read(self):
        import _io
        f = _io.BytesIO("hello")
        assert f.read() == "hello"
        import gc; gc.collect()
        assert f.read(8192) == ""
        f.close()

    def test_seek(self):
        import _io
        f = _io.BytesIO("hello")
        assert f.tell() == 0
        assert f.seek(-1, 2) == 4
        assert f.tell() == 4
        assert f.seek(0) == 0

    def test_truncate(self):
        import _io
        f = _io.BytesIO("hello")
        f.seek(3)
        assert f.truncate() == 3
        assert f.getvalue() == "hel"

    def test_setstate(self):
        # state is (content, position, __dict__)
        import _io
        f = _io.BytesIO("hello")
        content, pos, __dict__ = f.__getstate__()
        assert (content, pos) == ("hello", 0)
        assert __dict__ is None or __dict__ == {}
        f.__setstate__(("world", 3, {"a": 1}))
        assert f.getvalue() == "world"
        assert f.read() == "ld"
        assert f.a == 1
        assert f.__getstate__() == ("world", 5, {"a": 1})
        raises(TypeError, f.__setstate__, ("", 0))
        f.close()
        raises(ValueError, f.__getstate__)
        raises(ValueError, f.__setstate__, ("world", 3, {"a": 1}))

    def test_readinto(self):
        import _io

        b = _io.BytesIO("hello")
        b.close()
        raises(ValueError, b.readinto, bytearray("hello"))
