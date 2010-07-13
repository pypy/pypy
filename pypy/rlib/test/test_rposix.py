from pypy.rpython.test.test_llinterp import interpret
from pypy.tool.udir import udir
from pypy.rlib import rposix
import os

def ll_to_string(s):
    return ''.join(s.chars)

class TestPosixUnicode:
    def setup_class(cls):
        cls.ufilename = (unicode(udir.join('test_open')) +
                     u'\u65e5\u672c.txt') # "Japan"
        f = file(cls.ufilename, 'w')
        f.write("test")
        f.close()

        class UnicodeWithEncoding:
            def __init__(self, unistr):
                self.unistr = unistr

            def encode(self):
                from pypy.rlib.runicode import unicode_encode_utf_8
                return unicode_encode_utf_8(self.unistr, len(self.unistr),
                                            "strict")

            def gettext(self):
                return self.unistr

        cls.path = UnicodeWithEncoding(cls.ufilename)

    def test_access(self):
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
