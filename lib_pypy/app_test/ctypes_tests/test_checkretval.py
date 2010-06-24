import py
import sys

from ctypes import *

def setup_module(mod):
    import conftest
    mod.dll = CDLL(str(conftest.sofile))

class CHECKED(c_int):
    def _check_retval_(value):
        # Receives a CHECKED instance.
        return str(value.value)
    _check_retval_ = staticmethod(_check_retval_)

class TestRetval:

    def test_checkretval(self):
        assert 42 == dll._testfunc_p_p(42)

        dll._testfunc_p_p.restype = CHECKED
        assert "42" == dll._testfunc_p_p(42)

        dll._testfunc_p_p.restype = None
        assert None == dll._testfunc_p_p(42)

        del dll._testfunc_p_p.restype
        assert 42 == dll._testfunc_p_p(42)

    try:
        oledll
    except NameError:
        pass
    else:
        def test_oledll(self):
            raises(WindowsError,
                   oledll.oleaut32.CreateTypeLib2,
                   0, 0, 0)
