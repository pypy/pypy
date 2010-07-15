from pypy.rpython.test.test_llinterp import interpret
from pypy.tool.udir import udir
from pypy.rlib import rposix
import os, sys

def ll_to_string(s):
    return ''.join(s.chars)

class UnicodeWithEncoding:
    def __init__(self, unistr):
        self.unistr = unistr

    if sys.platform == 'win32':
        def encode(self):
            from pypy.rlib.runicode import unicode_encode_mbcs
            return unicode_encode_mbcs(self.unistr, len(self.unistr),
                                       "strict")
    else:
        def encode(self):
            from pypy.rlib.runicode import unicode_encode_utf_8
            return unicode_encode_utf_8(self.unistr, len(self.unistr),
                                        "strict")

    def gettext(self):
        return self.unistr

class TestPosixUnicode:
    def setup_method(self, method):
        self.ufilename = (unicode(udir.join('test_open')) +
                          u'\u65e5\u672c.txt') # "Japan"
        f = file(self.ufilename, 'w')
        f.write("test")
        f.close()

        self.path = UnicodeWithEncoding(self.ufilename)

    def test_open(self):
        def f():
            try:
                fd = rposix.open(self.path, os.O_RDONLY, 0777)
                try:
                    text = os.read(fd, 50)
                    return text
                finally:
                    os.close(fd)
            except OSError:
                return ''

        assert ll_to_string(interpret(f, [])) == "test"

    def test_stat(self):
        def f():
            return rposix.stat(self.path).st_mtime

        assert interpret(f, []) == os.stat(self.ufilename).st_mtime

    def test_access(self):
        def f():
            return rposix.access(self.path, os.R_OK)

        assert interpret(f, []) == 1

    def test_chmod(self):
        def f():
            return rposix.chmod(self.path, 0777)

        interpret(f, []) # does not crash

    def test_unlink(self):
        def f():
            return rposix.unlink(self.path)

        interpret(f, [])
        assert not os.path.exists(self.ufilename)

    def test_listdir(self):
        udir = UnicodeWithEncoding(os.path.dirname(self.ufilename))
        def f():
            return u', '.join(rposix.listdir(udir))

        result = interpret(f, [])
        assert os.path.basename(self.ufilename) in ll_to_string(result)

    def test_chdir(self):
        os.unlink(self.ufilename)

        def f():
            rposix.mkdir(self.path, 0777)
            rposix.chdir(self.path)

        curdir = os.getcwd()
        try:
            interpret(f, [])
            assert os.getcwdu() == self.ufilename
        finally:
            os.chdir(curdir)

        def g():
            rposix.rmdir(self.path)

        try:
            interpret(g, [])
        finally:
            try:
                os.rmdir(self.ufilename)
            except Exception:
                pass
