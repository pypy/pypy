from pypy.conftest import gettestobjspace

class AppTestBytesIO:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])

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
        f.close()

    def test_seek(self):
        import _io
        f = _io.BytesIO("hello")
        assert f.tell() == 0
        assert f.seek(-1, 2) == 4
        assert f.tell() == 4
        assert f.seek(0) == 0
