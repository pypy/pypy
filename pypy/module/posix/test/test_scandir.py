import sys, os
from rpython.tool.udir import udir
from pypy.module.posix.test import test_posix2


def _make_dir(dirname, content):
    d = os.path.join(str(udir), dirname)
    os.mkdir(d)
    for key, value in content.items():
        filename = os.path.join(d, key)
        if value == 'dir':
            os.mkdir(filename)
        elif value == 'file':
            with open(filename, 'w') as f:
                pass
        elif value == 'symlink-file':
            os.symlink(str(udir.ensure('some_file')), filename)
        elif value == 'symlink-dir':
            os.symlink(str(udir), filename)
        elif value == 'symlink-broken':
            os.symlink(filename + '-broken', filename)
        elif value == 'symlink-error':
            os.symlink(filename, filename)
        else:
            raise NotImplementedError(repr(value))
    return d.decode(sys.getfilesystemencoding())


class AppTestScandir(object):
    spaceconfig = {'usemodules': test_posix2.USEMODULES}

    def setup_class(cls):
        space = cls.space
        cls.w_posix = space.appexec([], test_posix2.GET_POSIX)
        cls.w_dir_empty = space.wrap(_make_dir('empty', {}))
        cls.w_dir0 = space.wrap(_make_dir('dir0', {'f1': 'file',
                                                   'f2': 'file',
                                                   'f3': 'file'}))
        cls.w_dir1 = space.wrap(_make_dir('dir1', {'file1': 'file'}))
        cls.w_dir2 = space.wrap(_make_dir('dir2', {'subdir2': 'dir'}))
        cls.w_dir3 = space.wrap(_make_dir('dir3', {'sfile3': 'symlink-file'}))
        cls.w_dir4 = space.wrap(_make_dir('dir4', {'sdir4': 'symlink-dir'}))
        cls.w_dir5 = space.wrap(_make_dir('dir5', {'sbrok5': 'symlink-broken'}))
        cls.w_dir6 = space.wrap(_make_dir('dir6', {'serr6': 'symlink-error'}))

    def test_scandir_empty(self):
        posix = self.posix
        sd = posix.scandir(self.dir_empty)
        assert list(sd) == []
        assert list(sd) == []

    def test_scandir_files(self):
        posix = self.posix
        sd = posix.scandir(self.dir0)
        names = [d.name for d in sd]
        assert sorted(names) == ['f1', 'f2', 'f3']

    def test_unicode_versus_bytes(self):
        posix = self.posix
        d = next(posix.scandir())
        assert type(d.name) is str
        assert type(d.path) is str
        assert d.path == './' + d.name
        d = next(posix.scandir(u'.'))
        assert type(d.name) is str
        assert type(d.path) is str
        assert d.path == './' + d.name
        d = next(posix.scandir(b'.'))
        assert type(d.name) is bytes
        assert type(d.path) is bytes
        assert d.path == b'./' + d.name
        d = next(posix.scandir('/'))
        assert type(d.name) is str
        assert type(d.path) is str
        assert d.path == '/' + d.name
        d = next(posix.scandir(b'/'))
        assert type(d.name) is bytes
        assert type(d.path) is bytes
        assert d.path == b'/' + d.name

    def test_dir1(self):
        posix = self.posix
        d = next(posix.scandir(self.dir1))
        assert d.name == 'file1'
        assert     d.is_file()
        assert not d.is_dir()
        assert not d.is_symlink()
        raises(TypeError, d.is_file, True)

    def test_dir2(self):
        posix = self.posix
        d = next(posix.scandir(self.dir2))
        assert d.name == 'subdir2'
        assert not d.is_file()
        assert     d.is_dir()
        assert not d.is_symlink()

    def test_dir3(self):
        posix = self.posix
        d = next(posix.scandir(self.dir3))
        assert d.name == 'sfile3'
        assert     d.is_file()
        assert not d.is_dir()
        assert     d.is_symlink()
        assert     d.is_file(follow_symlinks=True)
        assert not d.is_file(follow_symlinks=False)

    def test_dir4(self):
        posix = self.posix
        d = next(posix.scandir(self.dir4))
        assert d.name == 'sdir4'
        assert not d.is_file()
        assert     d.is_dir()
        assert     d.is_symlink()
        assert     d.is_dir(follow_symlinks=True)
        assert not d.is_dir(follow_symlinks=False)

    def test_dir5(self):
        posix = self.posix
        d = next(posix.scandir(self.dir5))
        assert d.name == 'sbrok5'
        assert not d.is_file()
        assert not d.is_dir()
        assert     d.is_symlink()

    def test_dir6(self):
        posix = self.posix
        d = next(posix.scandir(self.dir6))
        assert d.name == 'serr6'
        raises(OSError, d.is_file)
        raises(OSError, d.is_dir)
        assert d.is_symlink()
