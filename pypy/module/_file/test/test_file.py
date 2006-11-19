import py

from pypy.conftest import gettestobjspace

class AppTestFile(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=("_file", ))
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("foo.txt")))

    def test_simple(self):
        import _file
        f = _file.file(self.temppath, "w")
        try:
            f.write("foo")
        finally:
            f.close()
        f = _file.file(self.temppath, "r")
        try:
            s = f.read()
            assert s == "foo"
        finally:
            f.close()

    def test_fdopen(self):
        import _file, os
        f = _file.file(self.temppath, "w")
        try:
            f.write("foo")
        finally:
            f.close()
        fd = os.open(self.temppath, os.O_WRONLY | os.O_CREAT)
        f2 = _file.file.fdopen(fd, "a")
        f2.seek(0, 2)
        f2.write("bar")
        f2.close()
        # don't close fd, will get a whining __del__
        f = _file.file(self.temppath, "r")
        try:
            s = f.read()
            assert s == "foobar"
        finally:
            f.close()

    def test_badmode(self):
        import _file
        raises(IOError, _file.file, "foo", "bar")

    def test_wraposerror(self):
        import _file
        raises(IOError, _file.file, "hopefully/not/existant.bar")

    def test_correct_file_mode(self):
        import _file, os
        f = _file.file(self.temppath, "w")
        umask = os.umask(18)
        os.umask(umask)
        try:
            f.write("foo")
        finally:
            f.close()
        assert oct(os.stat(self.temppath).st_mode & 0777 | umask) == oct(0666)

    def test_newlines(self):
        import _file, os
        f = _file.file(self.temppath, "wb")
        f.write("\r\n")
        assert f.newlines is None
        f.close()
        f = _file.file(self.temppath, "rU")
        res = f.read()
        assert res == "\n"
        assert f.newlines == "\r\n"
