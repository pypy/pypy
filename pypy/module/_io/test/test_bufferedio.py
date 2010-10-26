from pypy.conftest import gettestobjspace
from pypy.interpreter.gateway import interp2app
from pypy.tool.udir import udir

class AppTestBufferedReader:
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
        raw = _io.FileIO(self.tmpfile)
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

class AppTestBufferedWriter:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])
        tmpfile = udir.join('tmpfile')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))
        def readfile(space):
            return space.wrap(tmpfile.read())
        cls.w_readfile = cls.space.wrap(interp2app(readfile))

    def test_write(self):
        import _io
        raw = _io.FileIO(self.tmpfile, 'w')
        f = _io.BufferedWriter(raw)
        f.write("abcd")
        f.close()
        assert self.readfile() == "abcd"

    def test_largewrite(self):
        import _io
        raw = _io.FileIO(self.tmpfile, 'w')
        f = _io.BufferedWriter(raw)
        f.write("abcd" * 5000)
        f.close()
        assert self.readfile() == "abcd" * 5000
