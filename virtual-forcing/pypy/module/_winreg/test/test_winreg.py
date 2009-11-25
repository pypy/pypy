from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir

import os, sys, py

if sys.platform != 'win32':
    py.test.skip("_winreg is a win32 module")

try:
    # To call SaveKey, the process must have Backup Privileges
    import win32api
    import win32security
    priv_flags = win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY
    hToken = win32security.OpenProcessToken (win32api.GetCurrentProcess (), priv_flags)
    privilege_id = win32security.LookupPrivilegeValue (None, "SeBackupPrivilege")
    win32security.AdjustTokenPrivileges (hToken, 0, [(privilege_id, win32security.SE_PRIVILEGE_ENABLED)])
except:
    canSaveKey = False
else:
    canSaveKey = True

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
        cls.w_canSaveKey = space.wrap(canSaveKey)
        cls.w_tmpfilename = space.wrap(str(udir.join('winreg-temp')))

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
        from _winreg import CreateKey, QueryInfoKey
        key = CreateKey(self.root_key, self.test_key_name)
        sub_key = CreateKey(key, "sub_key")

        nkeys, nvalues, since_mod = QueryInfoKey(key)
        assert nkeys == 1

        nkeys, nvalues, since_mod = QueryInfoKey(sub_key)
        assert nkeys == 0

    def test_close(self):
        from _winreg import OpenKey, CloseKey, FlushKey, QueryInfoKey
        key = OpenKey(self.root_key, self.test_key_name)
        sub_key = OpenKey(key, "sub_key")

        int_sub_key = int(sub_key)
        FlushKey(sub_key)
        CloseKey(sub_key)
        raises(EnvironmentError, QueryInfoKey, int_sub_key)

        int_key = int(key)
        key.Close()
        raises(EnvironmentError, QueryInfoKey, int_key)

        key = OpenKey(self.root_key, self.test_key_name)
        int_key = key.Detach()
        QueryInfoKey(int_key) # works
        key.Close()
        QueryInfoKey(int_key) # still works
        CloseKey(int_key)
        raises(EnvironmentError, QueryInfoKey, int_key) # now closed

    def test_exception(self):
        from _winreg import QueryInfoKey
        import errno
        try:
            QueryInfoKey(0)
        except EnvironmentError, e:
            assert e.winerror == 6
            assert e.errno == errno.EBADF
            # XXX translations...
            assert ("invalid" in e.strerror.lower() or
                    "non valide" in e.strerror.lower())
        else:
            assert 0, "Did not raise"

    def test_SetValueEx(self):
        from _winreg import CreateKey, SetValueEx
        key = CreateKey(self.root_key, self.test_key_name)
        sub_key = CreateKey(key, "sub_key")
        for name, value, type in self.test_data:
            SetValueEx(sub_key, name, 0, type, value)

    def test_readValues(self):
        from _winreg import OpenKey, EnumValue, QueryValueEx, EnumKey
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

        for name, value, type in self.test_data:
            assert QueryValueEx(sub_key, name) == (value, type)

        assert EnumKey(key, 0) == "sub_key"
        raises(EnvironmentError, EnumKey, key, 1)

    def test_delete(self):
        from _winreg import OpenKey, KEY_ALL_ACCESS, DeleteValue, DeleteKey
        key = OpenKey(self.root_key, self.test_key_name, 0, KEY_ALL_ACCESS)
        sub_key = OpenKey(key, "sub_key", 0, KEY_ALL_ACCESS)

        for name, value, type in self.test_data:
            DeleteValue(sub_key, name)

        DeleteKey(key, "sub_key")

    def test_connect(self):
        from _winreg import ConnectRegistry, HKEY_LOCAL_MACHINE
        h = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        h.Close()

    def test_savekey(self):
        if not self.canSaveKey:
            skip("CPython needs win32api to set the SeBackupPrivilege security privilege")
        from _winreg import OpenKey, KEY_ALL_ACCESS, SaveKey
        import os
        try:
            os.unlink(self.tmpfilename)
        except:
            pass

        key = OpenKey(self.root_key, self.test_key_name, 0, KEY_ALL_ACCESS)
        SaveKey(key, self.tmpfilename)
