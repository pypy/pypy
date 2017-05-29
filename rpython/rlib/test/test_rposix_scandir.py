import sys, os
import py
from rpython.rlib import rposix_scandir


class TestScanDir(object):

    @py.test.mark.skipif("sys.platform == 'win32'")   # XXX
    def test_name_bytes(self):
        scan = rposix_scandir.opendir('/')
        found = []
        while True:
            p = rposix_scandir.nextentry(scan)
            if not p:
                break
            assert rposix_scandir.has_name_bytes(p)
            found.append(rposix_scandir.get_name_bytes(p))
        rposix_scandir.closedir(scan)
        found.remove('.')
        found.remove('..')
        assert sorted(found) == sorted(os.listdir('/'))
