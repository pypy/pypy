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
        assert f.closefd is True
        f.close()

    def test_weakrefable(self):
        import _io
        from weakref import proxy
        f = _io.FileIO(self.tmpfile)
        p = proxy(f)
        assert p.mode == 'rb'
        f.close()

    def test_open_fd(self):
        import _io
        os = self.posix
        fd = os.open(self.tmpfile, os.O_RDONLY, 0666)
        f = _io.FileIO(fd, "rb", closefd=False)
        assert f.fileno() == fd
        assert f.closefd is False
        f.close()
        os.close(fd)

    def test_open_directory(self):
        import _io
        raises(IOError, _io.FileIO, self.tmpdir, "rb")

    def test_readline(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        assert f.readline() == 'a\n'
        assert f.readline() == 'b\n'
        assert f.readline() == 'c'
        assert f.readline() == ''
        f.close()

    def test_readlines(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        assert f.readlines() == ["a\n", "b\n", "c"]
        f.seek(0)
        assert f.readlines(3) == ["a\n", "b\n"]
        f.close()

    def test_readall(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        assert f.readall() == "a\nb\nc"
        f.close()

    def test_write(self):
        import _io
        filename = self.tmpfile + '_w'
        f = _io.FileIO(filename, 'wb')
        f.write("test")
        # try without flushing
        f2 = _io.FileIO(filename, 'rb')
        assert f2.read() == "test"
        f.close()
        f2.close()

    def test_writelines(self):
        import _io
        filename = self.tmpfile + '_w'
        f = _io.FileIO(filename, 'wb')
        f.writelines(["line1\n", "line2", "line3"])
        f2 = _io.FileIO(filename, 'rb')
        assert f2.read() == "line1\nline2line3"
        f.close()
        f2.close()

    def test_seek(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        f.seek(0)
        self.posix.close(f.fileno())
        raises(IOError, f.seek, 0)

    def test_tell(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'rb')
        f.seek(3)
        assert f.tell() == 3
        f.close()

    def test_truncate(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'r+b')
        assert f.truncate(100) == 100 # grow the file
        f.close()
        f = _io.FileIO(self.tmpfile)
        assert len(f.read()) == 100
        f.close()
        #
        f = _io.FileIO(self.tmpfile, 'r+b')
        f.seek(50)
        assert f.truncate() == 50
        f.close()
        f = _io.FileIO(self.tmpfile)
        assert len(f.read()) == 50
        f.close()

    def test_readinto(self):
        import _io
        a = bytearray('x' * 10)
        f = _io.FileIO(self.tmpfile, 'r+')
        assert f.readinto(a) == 10
        f.close()
        assert a == 'a\nb\nc\0\0\0\0\0'
        #
        a = bytearray('x' * 10)
        f = _io.FileIO(self.tmpfile, 'r+')
        f.truncate(3)
        assert f.readinto(a) == 3
        f.close()
        assert a == 'a\nbxxxxxxx'

    def test_repr(self):
        import _io
        f = _io.FileIO(self.tmpfile, 'r')
        assert repr(f) == ("<_io.FileIO name=%r mode='%s'>"
                           % (f.name, f.mode))
        del f.name
        assert repr(f) == ("<_io.FileIO fd=%r mode='%s'>"
                           % (f.fileno(), f.mode))
        f.close()
        assert repr(f) == "<_io.FileIO [closed]>"

