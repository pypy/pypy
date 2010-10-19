from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir
import os

class AppTestFileIO:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])
        tmpfile = udir.join('tmpfile')
        tmpfile.write("a\nb\nc", mode='wb')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))
        cls.w_tmpdir = cls.space.wrap(str(udir))
        cls.w_posix = cls.space.appexec([], """():
            import %s as m;
            return m""" % os.name)

    def test_constructor(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'a')
        assert f.name.endswith('tmpfile')
        assert f.mode == 'wb'
        f.close()

    def test_open_fd(self):
        import _io
        os = self.posix
        fd = os.open(self.tmpfile, os.O_RDONLY, 0666)
        f = _io.FileIO(fd, "rb")
        assert f.fileno() == fd
        f.close()

    def test_open_directory(self):
        import _io
        raises(OSError, _io.FileIO, self.tmpdir, "rb")

    def test_readline(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        f.seek(0)
        assert f.readline() == 'a\n'
        assert f.readline() == 'b\n'
        assert f.readline() == 'c'
        assert f.readline() == ''
        f.close()
