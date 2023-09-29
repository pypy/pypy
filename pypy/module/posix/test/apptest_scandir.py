import pytest

import sys
try:
    import nt as posix
except ImportError:
    import posix
os = posix

has_os_symlink = hasattr(os, 'symlink')


def _make_dir(dirname, content):
    d = os.path.join(tmp_path, dirname)
    os.mkdir(d)
    for key, value in content.items():
        filename = os.path.join(d, key)
        if value == 'dir':
            os.mkdir(filename)
        elif value == 'file':
            with open(filename, 'w') as f:
                pass
        elif value == 'symlink-file':
            os.symlink('some_file', filename)
        elif value == 'symlink-dir':
            os.symlink(tmp_path, filename)
        elif value == 'symlink-broken':
            os.symlink(filename + '-broken', filename)
        elif value == 'symlink-error':
            os.symlink(filename, filename)
        else:
            raise NotImplementedError(repr(value))
    return d


class TestScandir(object):

    @classmethod
    def setup_class(cls):
        cls.dir_empty = _make_dir('empty', {})
        cls.dir0 = _make_dir('dir0', {'f1': 'file',
                                      'f2': 'file',
                                      'f3': 'file'})
        cls.dir1 = _make_dir('dir1', {'file1': 'file'})
        cls.dir2 = _make_dir('dir2', {'subdir2': 'dir'})
        if has_os_symlink:
            cls.dir3 = _make_dir('dir3', {'sfile3': 'symlink-file'})
            cls.dir4 = _make_dir('dir4', {'sdir4': 'symlink-dir'})
            cls.dir5 = _make_dir('dir5', {'sbrok5': 'symlink-broken'})
            cls.dir6 = _make_dir('dir6', {'serr6': 'symlink-error'})

    def test_scandir_empty(self):
        sd = os.scandir(self.dir_empty)
        assert list(sd) == []

    def test_scandir_files(self):
        sd = os.scandir(self.dir0)
        names = [d.name for d in sd]
        assert sorted(names) == ['f1', 'f2', 'f3']

    def test_unicode_versus_bytes(self):
        d = next(os.scandir())
        assert type(d.name) is str
        assert type(d.path) is str
        assert d.path == '.' + os.sep + d.name
        d = next(os.scandir(None))
        assert type(d.name) is str
        assert type(d.path) is str
        assert d.path == '.' + os.sep + d.name
        d = next(os.scandir(u'.'))
        assert type(d.name) is str
        assert type(d.path) is str
        assert d.path == '.' + os.sep + d.name
        d = next(os.scandir(os.sep))
        assert type(d.name) is str
        assert type(d.path) is str
        assert d.path == os.sep + d.name
        d = next(os.scandir(b'.'))
        assert type(d.name) is bytes
        assert type(d.path) is bytes
        assert d.path == b'.' + os.sep.encode('ascii') + d.name
        d = next(os.scandir(b'/'))
        assert type(d.name) is bytes
        assert type(d.path) is bytes
        assert d.path == b'/' + d.name

    def test_stat1(self):
        d = next(os.scandir(self.dir1))
        assert d.name == 'file1'
        assert d.stat().st_mode & 0o170000 == 0o100000    # S_IFREG
        assert d.stat().st_size == 0

    @pytest.mark.skipif(not has_os_symlink, reason="no symlink support")
    def test_stat4(self):
        d = next(os.scandir(self.dir4))
        assert d.name == 'sdir4'
        assert d.stat().st_mode & 0o170000 == 0o040000    # S_IFDIR
        assert d.stat(follow_symlinks=True).st_mode &0o170000 == 0o040000
        assert d.stat(follow_symlinks=False).st_mode&0o170000 == 0o120000 #IFLNK

    def test_dir1(self):
        d = next(os.scandir(self.dir1))
        assert d.name == 'file1'
        assert     d.is_file()
        assert not d.is_dir()
        assert not d.is_symlink()
        with pytest.raises(TypeError):
            assert d.is_file()
        assert     d.is_file(follow_symlinks=False)
        assert not d.is_dir(follow_symlinks=False)

    def test_dir2(self):
        d = next(os.scandir(self.dir2))
        assert d.name == 'subdir2'
        assert not d.is_file()
        assert     d.is_dir()
        assert not d.is_symlink()
        assert not d.is_file(follow_symlinks=False)
        assert     d.is_dir(follow_symlinks=False)

    @pytest.mark.skipif(not has_os_symlink, reason="no symlink support")
    def test_dir3(self):
        d = next(os.scandir(self.dir3))
        assert d.name == 'sfile3'
        assert     d.is_file()
        assert not d.is_dir()
        assert     d.is_symlink()
        assert     d.is_file(follow_symlinks=True)
        assert not d.is_file(follow_symlinks=False)

    @pytest.mark.skipif(not has_os_symlink, reason="no symlink support")
    def test_dir4(self):
        d = next(os.scandir(self.dir4))
        assert d.name == 'sdir4'
        assert not d.is_file()
        assert     d.is_dir()
        assert     d.is_symlink()
        assert     d.is_dir(follow_symlinks=True)
        assert not d.is_dir(follow_symlinks=False)

    @pytest.mark.skipif(not has_os_symlink, reason="no symlink support")
    def test_dir5(self):
        d = next(os.scandir(self.dir5))
        assert d.name == 'sbrok5'
        assert not d.is_file()
        assert not d.is_dir()
        assert     d.is_symlink()
        with pytest.raises(OSError):
            d.stat()

    @pytest.mark.skipif(not has_os_symlink, reason="no symlink support")
    def test_dir6(self):
        d = next(os.scandir(self.dir6))
        assert d.name == 'serr6'
        with pytest.raises(OSError):
            d.is_file()
        with pytest.raises(OSError):
            d.is_dir()
        assert d.is_symlink()

    def test_fdopendir(self):
        import stat
        if 'HAVE_FDOPENDIR' in posix._have_functions:
            with pytest.raises(OSError):
                os.scandir(1234)
            # do like shutil._rmtree_safe_fd
            topfd = os.open(self.dir2, os.O_RDONLY)
            try:
                with os.scandir(topfd) as scandir_it:
                    entries = list(scandir_it)
                assert len(entries) > 0
                entry = entries[0]
                stat_val = entry.stat(follow_symlinks=False)
                assert stat.S_ISDIR(stat_val.st_mode)
            finally:
                os.close(topfd)
            fd = os.open(self.dir0 + os.sep + 'f1', os.O_RDONLY)
            try:
                with pytest.raises(NotADirectoryError):
                    os.scandir(fd)
            finally:
                os.close(fd)
        else:
            with pytest.raises(TypeError):
                os.scandir(1234)

    @pytest.mark.skipif(sys.platform == "win32", reason="no inode support")
    def test_inode(self):
        d = next(os.scandir(self.dir1))
        assert d.name == 'file1'
        ino = d.inode()
        assert ino == d.stat().st_ino

    def test_repr(self):
        d = next(os.scandir(self.dir1))
        assert isinstance(d, os.DirEntry)
        assert repr(d) == "<DirEntry 'file1'>"

    def test_direntry_unpicklable(self):
        import pickle
        d = next(os.scandir(self.dir1))
        with pytest.raises(TypeError):
            pickle.dumps(d)

    def test_fspath(self):
        d = next(os.scandir(self.dir1))
        assert os.fspath(d).endswith('dir1' + os.sep + 'file1')

    def test_resource_warning(self):
        import warnings, gc
        iterator = os.scandir(self.dir1)
        next(iterator)
        with warnings.catch_warnings(record=True) as l:
            warnings.simplefilter("always")
            del iterator
            gc.collect()
        assert isinstance(l[0].message, ResourceWarning)
        #
        iterator = os.scandir(self.dir1)
        next(iterator)
        with warnings.catch_warnings(record=True) as l:
            warnings.simplefilter("always")
            iterator.close()
            del iterator
            gc.collect()
        assert len(l) == 0

    def test_context_manager(self):
        import warnings, gc
        with warnings.catch_warnings(record=True) as l:
            warnings.simplefilter("always")
            with os.scandir(self.dir1) as iterator:
                next(iterator)
            del iterator
            gc.collect()
        assert not l

    def test_lstat(self):
        d = next(os.scandir(self.dir1))
        with open(d) as fp:
            length = len(fp.read())
        assert os.lstat(d).st_size == length
