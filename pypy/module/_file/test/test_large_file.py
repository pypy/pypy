import py, sys

from pypy.module._file.test.test_file import getfile

class AppTestLargeFile(object):
    spaceconfig = dict(usemodules=("_file",))

    def setup_class(cls):
        cls.w_temppath = cls.space.wrap(
            str(py.test.ensuretemp("fileimpl").join("large.data")))
        cls.w_file = getfile(cls.space)

    def setup_method(self, meth):
        if getattr(meth, 'need_sparse_files', False):
            from rpython.translator.c.test.test_extfunc import need_sparse_files
            if sys.maxsize < 2**32 and not self.runappdirect:
                # this fails because it uses ll2ctypes to call the posix
                # functions like 'open' and 'lseek', whereas a real compiled
                # C program would macro-define them to their longlong versions
                py.test.skip("emulation of files can't use "
                             "larger-than-long offsets")
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
