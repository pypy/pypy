
from pypy.conftest import gettestobjspace

class AppTestExc(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('exceptions',))

    def test_baseexc(self):
        from exceptions import BaseException

        assert str(BaseException()) == ''
        assert repr(BaseException()) == 'BaseException()'
        assert BaseException().message == ''
        assert BaseException(3).message == 3
        assert repr(BaseException(3)) == 'BaseException(3,)'
        assert str(BaseException(3)) == '3'
        assert BaseException().args == ()
        assert BaseException(3).args == (3,)
        assert BaseException(3, "x").args == (3, "x")
        assert repr(BaseException(3, "x")) == "BaseException(3, 'x')"
        assert str(BaseException(3, "x")) == "(3, 'x')"
        assert BaseException(3, "x").message == ''
        x = BaseException()
        x.xyz = 3
        assert x.xyz == 3
        x.args = [42]
        assert x.args == (42,)
        assert str(x) == '42'
        assert x[0] == 42
        x.args = (1, 2, 3)
        assert x[1:2] == (2,)
        x.message = "xyz"
        assert x.message == "xyz"

    def test_kwargs(self):
        from exceptions import Exception
        class X(Exception):
            def __init__(self, x=3):
                self.x = x

        x = X(x=8)
        assert x.x == 8

    def test_catch_with_unpack(self):
        from exceptions import LookupError

        try:
            raise LookupError(1, 2)
        except LookupError, (one, two):
            assert one == 1
            assert two == 2

    def test_exc(self):
        from exceptions import Exception, BaseException

        assert issubclass(Exception, BaseException)
        assert isinstance(Exception(), Exception)
        assert isinstance(Exception(), BaseException)
        assert repr(Exception(3, "x")) == "Exception(3, 'x')"
        assert str(IOError("foo", "bar")) == "[Errno foo] bar"

    def test_custom_class(self):
        from exceptions import Exception, BaseException, LookupError

        class MyException(Exception):
            def __init__(self, x):
                self.x = x

            def __str__(self):
                return self.x

        assert issubclass(MyException, Exception)
        assert issubclass(MyException, BaseException)
        assert not issubclass(MyException, LookupError)
        assert str(MyException("x")) == "x"

    def test_unicode_translate_error(self):
        from exceptions import UnicodeTranslateError
        ut = UnicodeTranslateError(u"x", 1, 5, "bah")
        assert ut.object == u'x'
        assert ut.start == 1
        assert ut.end == 5
        assert ut.reason == 'bah'
        assert ut.args == (u'x', 1, 5, 'bah')
        assert ut.message == ''
        ut.object = u'y'
        assert ut.object == u'y'
        assert str(ut) == "can't translate characters in position 1-4: bah"
        ut.start = 4
        ut.object = u'012345'
        assert str(ut) == "can't translate character u'\\x34' in position 4: bah"
        ut.object = []
        assert ut.object == []

    def test_key_error(self):
        from exceptions import KeyError

        assert str(KeyError('s')) == "'s'"

    def test_environment_error(self):
        from exceptions import EnvironmentError
        ee = EnvironmentError(3, "x", "y")
        assert str(ee) == "[Errno 3] x: 'y'"
        assert str(EnvironmentError(3, "x")) == "[Errno 3] x"
        assert ee.errno == 3
        assert ee.strerror == "x"
        assert ee.filename == "y"
        assert EnvironmentError(3, "x").filename is None

    def test_windows_error(self):
        try:
            from exceptions import WindowsError
        except ImportError:
            skip('WindowsError not present')
        ee = WindowsError(3, "x", "y")
        assert str(ee) == "[Error 3] x: y"
        # winerror=3 (ERROR_PATH_NOT_FOUND) maps to errno=2 (ENOENT)
        assert ee.winerror == 3
        assert ee.errno == 2
        assert str(WindowsError(3, "x")) == "[Error 3] x"

    def test_syntax_error(self):
        from exceptions import SyntaxError
        s = SyntaxError(3)
        assert str(s) == '3'
        assert str(SyntaxError("a", "b", 123)) == "a"
        assert str(SyntaxError("a", (1, 2, 3, 4))) == "a (line 2)"
        s = SyntaxError("a", (1, 2, 3, 4))
        assert s.msg == "a"
        assert s.filename == 1
        assert str(SyntaxError("msg", ("file.py", 2, 3, 4))) == "msg (file.py, line 2)"

    def test_system_exit(self):
        from exceptions import SystemExit
        assert SystemExit().code is None
        assert SystemExit("x").code == "x"
        assert SystemExit(1, 2).code == (1, 2)

    def test_unicode_decode_error(self):
        from exceptions import UnicodeDecodeError
        ud = UnicodeDecodeError("x", "y", 1, 5, "bah")
        assert ud.encoding == 'x'
        assert ud.object == 'y'
        assert ud.start == 1
        assert ud.end == 5
        assert ud.reason == 'bah'
        assert ud.args == ('x', 'y', 1, 5, 'bah')
        assert ud.message == ''
        ud.object = 'z9'
        assert ud.object == 'z9'
        assert str(ud) == "'x' codec can't decode bytes in position 1-4: bah"
        ud.end = 2
        assert str(ud) == "'x' codec can't decode byte 0x39 in position 1: bah"

    def test_unicode_encode_error(self):
        from exceptions import UnicodeEncodeError
        ue = UnicodeEncodeError("x", u"y", 1, 5, "bah")
        assert ue.encoding == 'x'
        assert ue.object == u'y'
        assert ue.start == 1
        assert ue.end == 5
        assert ue.reason == 'bah'
        assert ue.args == ('x', u'y', 1, 5, 'bah')
        assert ue.message == ''
        ue.object = u'z9'
        assert ue.object == u'z9'
        assert str(ue) == "'x' codec can't encode characters in position 1-4: bah"
        ue.end = 2
        assert str(ue) == "'x' codec can't encode character u'\\x39' in position 1: bah"
        ue.object = []
        assert ue.object == []
        raises(TypeError, UnicodeEncodeError, "x", "y", 1, 5, "bah")
        raises(TypeError, UnicodeEncodeError, u"x", u"y", 1, 5, "bah")

    def test_multiple_inheritance(self):
        from exceptions import LookupError, ValueError, Exception
        class A(LookupError, ValueError):
            pass
        assert issubclass(A, A)
        assert issubclass(A, Exception)
        assert issubclass(A, LookupError)
        assert issubclass(A, ValueError)
        assert not issubclass(A, KeyError)
        a = A()
        assert isinstance(a, A)
        assert isinstance(a, Exception)
        assert isinstance(a, LookupError)
        assert isinstance(a, ValueError)
        assert not isinstance(a, KeyError)

        from exceptions import UnicodeDecodeError, UnicodeEncodeError
        try:
            class B(UnicodeTranslateError, UnicodeEncodeError):
                pass
        except TypeError:
            pass
        else:
            fail("bah")

    def test_doc_and_module(self):
        import exceptions
        for name, e in exceptions.__dict__.items():
            if isinstance(e, type) and issubclass(e, exceptions.BaseException):
                assert e.__doc__, e
                assert e.__module__ == 'exceptions', e

    def test_reduce(self):
        from exceptions import LookupError, EnvironmentError

        le = LookupError(1, 2, "a")
        assert le.__reduce__() == (LookupError, (1, 2, "a"))
        le.xyz = (1, 2)
        assert le.__reduce__() == (LookupError, (1, 2, "a"), {"xyz": (1, 2)})
        ee = EnvironmentError(1, 2, "a")
        assert ee.__reduce__() == (EnvironmentError, (1, 2, "a"))

    def test_setstate(self):
        from exceptions import FutureWarning

        fw = FutureWarning()
        fw.__setstate__({"xyz": (1, 2)})
        assert fw.xyz == (1, 2)
        fw.__setstate__({'z': 1})
        assert fw.z == 1
        assert fw.xyz == (1, 2)

