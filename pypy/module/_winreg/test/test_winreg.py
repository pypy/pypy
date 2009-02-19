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
        k = _winreg.HKEYType(0x123)
        assert str(k) == "<PyHKEY:0x123>"

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
        try:
            _winreg.DeleteKey(cls.root_key, cls.test_key_name)
        except WindowsError:
            pass

    def test_simple_write(self):
        from _winreg import SetValue, QueryValue, REG_SZ
        value = "Some Default value"
        SetValue(self.root_key, self.test_key_name, REG_SZ, value)
        assert QueryValue(self.root_key, self.test_key_name) == value

    def test_CreateKey(self):
        from _winreg import CreateKey, CloseKey, QueryInfoKey
        key = CreateKey(self.root_key, self.test_key_name)
        sub_key = CreateKey(key, "sub_key")

        nkeys, nvalues, since_mod = QueryInfoKey(key)
        assert nkeys == 1

        nkeys, nvalues, since_mod = QueryInfoKey(sub_key)
        assert nkeys == 0

        int_sub_key = int(sub_key)
        CloseKey(sub_key)
        raises(EnvironmentError, QueryInfoKey, int_sub_key)

        int_key = int(key)
        key.Close()
        raises(EnvironmentError, QueryInfoKey, int_key)

    def test_exception(self):
        from _winreg import QueryInfoKey
        import errno
        try:
            QueryInfoKey(0)
        except EnvironmentError, e:
            assert e.winerror == 6
            assert e.errno == errno.EBADF
            assert "invalid" in e.strerror.lower()
        else:
            assert 0, "Did not raise"

    def test_SetValueEx(self):
        from _winreg import CreateKey, SetValueEx
        from _winreg import REG_DWORD, REG_SZ, REG_EXPAND_SZ
        from _winreg import REG_MULTI_SZ, REG_BINARY
        key = CreateKey(self.root_key, self.test_key_name)
        SetValueEx(key, "Int Value", 0,
                   REG_DWORD, 45)
        SetValueEx(key, "Str Value", 0,
                   REG_SZ, "A string Value")
        SetValueEx(key, "Unicode Value", 0,
                   REG_SZ, u"A unicode Value")
        SetValueEx(key, "Str Expand", 0,
                   REG_EXPAND_SZ, "The path is %path%")
        SetValueEx(key, "Multi Str", 0,
                   REG_MULTI_SZ, ["Several", "string", u"values"])
        SetValueEx(key, "Raw data", 0,
                   REG_BINARY, "binary"+chr(0)+"data")
