import sys, os
from rpython.tool.udir import udir
from pypy.module.posix.test import test_posix2


def _make_dir(dirname, content):
    d = os.path.join(str(udir), dirname)
    os.mkdir(d)
    for key, value in content.items():
        xxx
    return d.decode(sys.getfilesystemencoding())


class AppTestScandir(object):
    spaceconfig = {'usemodules': test_posix2.USEMODULES}

    def setup_class(cls):
        space = cls.space
        cls.w_posix = space.appexec([], test_posix2.GET_POSIX)
        cls.w_dir_empty = space.wrap(_make_dir('empty', {}))

    def test_scandir_empty(self):
        posix = self.posix
        sd = posix.scandir(self.dir_empty)
        assert list(sd) == []
        assert list(sd) == []

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
