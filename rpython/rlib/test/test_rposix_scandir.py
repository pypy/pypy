import sys, os
import py
from rpython.rlib import rposix_scandir

if sys.platform == 'win32':
    basedir = os.environ.get('LOCALAPPDATA', r'C:\users')
    func = rposix_scandir.get_name_unicode
else:
    basedir = '/'
    func = rposix_scandir.get_name_bytes

class TestScanDir(object):

    def test_name_bytes(self):
        scan = rposix_scandir.opendir(basedir)
        found = []
        while True:
            p = rposix_scandir.nextentry(scan)
            if not p:
                break
            found.append(func(p))
        rposix_scandir.closedir(scan)
        found.remove('.')
        found.remove('..')
        assert sorted(found) == sorted(os.listdir(basedir))
