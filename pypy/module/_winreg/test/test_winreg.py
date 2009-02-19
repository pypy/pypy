from pypy.conftest import gettestobjspace

import os, sys, py

if sys.platform != 'win32':
    py.test.skip("_winreg is a win32 module")

class AppTestHKey:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_winreg',))
        cls.space = space

    def test_repr(self):
        import _winreg
        k = _winreg.HKEYType(123)
        assert str(k) == "<PyHKEY:123>"

class AppTestFfi:
    def setup_class(cls):
        import _winreg
        space = gettestobjspace(usemodules=('_winreg',))
        cls.space = space
        cls.root_key = _winreg.HKEY_CURRENT_USER
        cls.test_key_name = "SOFTWARE\\Pypy Registry Test Key - Delete Me"
        cls.w_root_key = space.wrap(cls.root_key)
        cls.w_test_key_name = space.wrap(cls.test_key_name)

    def teardown_class(cls):
        import _winreg
        return
        try:
            _winreg.DeleteKey(cls.root_key, cls.test_key_name)
        except WindowsError:
            pass

    def test_simple_write(self):
        from _winreg import SetValue, QueryValue, REG_SZ
        value = "Some Default value"
        SetValue(self.root_key, self.test_key_name, REG_SZ, value)
        assert QueryValue(self.root_key, self.test_key_name) == value
