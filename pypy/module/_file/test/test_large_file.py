import py

from pypy.conftest import gettestobjspace
from pypy.module._file.test.test_file import getfile

class AppTestLargeFile(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=("_file", ))
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("large.data")))
        cls.w_file = getfile(cls.space)

    def setup_method(self, meth):
        if getattr(meth, 'need_sparse_files', False):
            from pypy.module.posix.test.test_posix2 import need_sparse_files
            need_sparse_files()

    def test_large_seek_offsets(self):
        FAR = 0x122223333
        f = self.file(self.temppath, "w+b")
        f.write("hello world")
        f.seek(FAR)
        assert f.tell() == FAR
        f.seek(-10, 1)
        assert f.tell() == FAR - 10
        f.seek(0x123456789, 1)
        assert f.tell() == FAR - 10 + 0x123456789
        f.seek(-FAR, 1)
        assert f.tell() == -10 + 0x123456789
        f.seek(FAR, 2)
        assert f.tell() == len("hello world") + FAR
        f.close()

    def test_large_sparse(self):
        FAR = 0x122223333
        f = self.file(self.temppath, "w+b")
        f.seek(FAR)
        f.write('end')
        f.seek(0)
        data = f.read(1234)
        assert data == 1234 * '\x00'
        f.seek(FAR-2-1234, 1)
        data = f.read(4321)
        assert data == '\x00\x00end'
        f.seek(-1, 2)
        assert f.tell() == FAR + 2
        f.truncate()
        f.seek(0, 2)
        assert f.tell() == FAR + 2
        f.truncate(FAR + 1)
        f.seek(FAR-2, 0)
        data = f.read(1)
        assert data == '\x00'
        assert f.tell() == FAR - 1
        data = f.read(1)
        assert data == '\x00'
        data = f.read(1)
        assert data == 'e'
        data = f.read(1)
        assert data == ''
        assert f.tell() == FAR + 1
        import sys
        if FAR > sys.maxint:
            f.seek(0)
            raises(OverflowError, f.read, FAR)
            raises(OverflowError, f.readline, FAR)
            raises(OverflowError, f.readlines, FAR)
        f.close()
    test_large_sparse.need_sparse_files = True
