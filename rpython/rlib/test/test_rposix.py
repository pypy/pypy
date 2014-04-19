from rpython.rtyper.test.test_llinterp import interpret
from rpython.tool.udir import udir
from rpython.rlib import rposix
import os, sys
import py

def ll_to_string(s):
    return ''.join(s.chars)

class UnicodeWithEncoding:
    def __init__(self, unistr):
        self.unistr = unistr

    if sys.platform == 'win32':
        def as_bytes(self):
            from rpython.rlib.runicode import unicode_encode_mbcs
            return unicode_encode_mbcs(self.unistr, len(self.unistr),
                                       "strict")
    else:
        def as_bytes(self):
            from rpython.rlib.runicode import unicode_encode_utf_8
            return unicode_encode_utf_8(self.unistr, len(self.unistr),
                                        "strict")

    def as_unicode(self):
        return self.unistr

class BasePosixUnicodeOrAscii:
    def setup_method(self, method):
        self.ufilename = self._get_filename()
        try:
            f = file(self.ufilename, 'w')
        except UnicodeEncodeError:
            py.test.skip("encoding not good enough")
        f.write("test")
        f.close()
        if sys.platform == 'win32' and isinstance(self.ufilename, str):
            self.path = self.ufilename
            self.path2 = self.ufilename + ".new"
        else:
            self.path  = UnicodeWithEncoding(self.ufilename)
            self.path2 = UnicodeWithEncoding(self.ufilename + ".new")

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
        if sys.platform == 'win32':
            # double vs. float, be satisfied with sub-millisec resolution
            assert abs(interpret(f, []) - os.stat(self.ufilename).st_mtime) < 1e-4
        else:
            assert interpret(f, []) == os.stat(self.ufilename).st_mtime

    def test_access(self):
        def f():
            return rposix.access(self.path, os.R_OK)

        assert interpret(f, []) == 1

    def test_utime(self):
        def f():
            return rposix.utime(self.path, None)

        interpret(f, []) # does not crash

    def test_chmod(self):
        def f():
            return rposix.chmod(self.path, 0777)

        interpret(f, []) # does not crash

    def test_unlink(self):
        def f():
            return rposix.unlink(self.path)

        interpret(f, [])
        assert not os.path.exists(self.ufilename)

    def test_rename(self):
        def f():
            return rposix.rename(self.path, self.path2)

        interpret(f, [])
        assert not os.path.exists(self.ufilename)
        assert os.path.exists(self.ufilename + '.new')

    def test_listdir(self):
        udir = UnicodeWithEncoding(os.path.dirname(self.ufilename))

        if sys.platform == 'win32':
            def f():
                if isinstance(udir.as_unicode(), str):
                    _udir = udir.as_unicode()
                else:
                    _udir = udir
                return u', '.join(rposix.listdir(_udir))
            result = interpret(f, [])
            assert os.path.basename(self.ufilename) in ll_to_string(result)
        else:
            def f():
                return ', '.join(rposix.listdir(udir))
            result = interpret(f, [])
            assert (os.path.basename(self.ufilename).encode('utf-8') in
                    ll_to_string(result))

    def test_chdir(self):
        os.unlink(self.ufilename)

        def f():
            rposix.mkdir(self.path, 0777)
            rposix.chdir(self.path)

        curdir = os.getcwd()
        try:
            interpret(f, [])
            assert os.getcwdu() == os.path.realpath(self.ufilename)
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

    def test_is_valid_fd(self):
        if os.name != 'nt':
            py.test.skip('relevant for windows only')
        assert rposix.is_valid_fd(0) == 1
        fid = open(str(udir.join('validate_test.txt')), 'w')
        fd = fid.fileno()
        assert rposix.is_valid_fd(fd) == 1
        fid.close()
        assert rposix.is_valid_fd(fd) == 0

    def test_putenv(self):
        def f():
            rposix.putenv(self.path, self.path)
            rposix.unsetenv(self.path)

        interpret(f, []) # does not crash


class TestPosixAscii(BasePosixUnicodeOrAscii):
    def _get_filename(self):
        return str(udir.join('test_open_ascii'))

class TestPosixUnicode(BasePosixUnicodeOrAscii):
    def _get_filename(self):
        return (unicode(udir.join('test_open')) +
                u'\u65e5\u672c.txt') # "Japan"
