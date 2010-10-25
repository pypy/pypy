from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir

class AppTestBufferedIO:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])
        tmpfile = udir.join('tmpfile')
        tmpfile.write("a\nb\nc", mode='wb')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))

    def test_simple_read(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.read() == "a\nb\nc"
        f.close()
        #
        raw.seek(0)
        f = _io.BufferedReader(raw)
        r = f.read(4)
        assert r == "a\nb\n"
        f.close()

    def test_seek(self):
        import _io
        raw = _io.FileIO(self.tmpfile)
        f = _io.BufferedReader(raw)
        assert f.read() == "a\nb\nc"
        f.seek(0)
        assert f.read() == "a\nb\nc"
        f.seek(-2, 2)
        assert f.read() == "\nc"
        f.close()
