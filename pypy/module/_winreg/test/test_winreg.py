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

        test_data = [
            ("Int Value", 45, _winreg.REG_DWORD),
            ("Str Value", "A string Value", _winreg.REG_SZ),
            ("Unicode Value", u"A unicode Value", _winreg.REG_SZ),
            ("Str Expand", "The path is %path%", _winreg.REG_EXPAND_SZ),
            ("Multi Str", ["Several", "string", u"values"], _winreg.REG_MULTI_SZ),
            ("Raw data", "binary"+chr(0)+"data", _winreg.REG_BINARY),
            ]
        cls.w_test_data = space.wrap(test_data)

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
        key = CreateKey(self.root_key, self.test_key_name)
        sub_key = CreateKey(key, "sub_key")
        for name, value, type in self.test_data:
            SetValueEx(sub_key, name, 0, type, value)

    def test_readValues(self):
        from _winreg import OpenKey, EnumValue, QueryValueEx
        key = OpenKey(self.root_key, self.test_key_name)
        sub_key = OpenKey(key, "sub_key")
        index = 0
        while 1:
            try:
                data = EnumValue(sub_key, index)
            except EnvironmentError, e:
                break
            assert data in self.test_data
            index = index + 1
        assert index == len(self.test_data)

        for name, data, type in self.test_data:
            assert QueryValueEx(sub_key, name) == (data, type)
