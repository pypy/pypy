import sys
import __pypy__

class TestHook:
    def __init__(self, raise_on_events=None, exc_type=RuntimeError):
        self.raise_on_events = raise_on_events or ()
        self.exc_type = exc_type
        self.seen = []
        self.closed = False

    def __enter__(self, *a):
        sys.addaudithook(self)
        return self

    def __exit__(self, *a):
        self.close()
        __pypy__._testing_clear_audithooks()

    def close(self):
        self.closed = True

    @property
    def seen_events(self):
        return [i[0] for i in self.seen]

    def __call__(self, event, args):
        if self.closed:
            return
        if not event.startswith("winreg."):
            return
        self.seen.append((event, args))
        if event in self.raise_on_events:
            raise self.exc_type("saw event " + event)

def test_ConnectRegistry():
    from winreg import ConnectRegistry, HKEY_LOCAL_MACHINE
    machine = u"This is a long computer name that doesn't exist, hopefully"
    with TestHook() as hook:
        try:
            ConnectRegistry(machine, HKEY_LOCAL_MACHINE)
        except OSError:
            pass
    assert hook.seen[0] == ("winreg.ConnectRegistry", (machine, HKEY_LOCAL_MACHINE))

def test_CreateKey():
    from winreg import CreateKey, CreateKeyEx
    from winreg import HKEY_CURRENT_USER, KEY_ALL_ACCESS, KEY_WRITE
    with TestHook() as hook:
        key = CreateKey(HKEY_CURRENT_USER, u"SOFTWARE")
        sub_key = CreateKeyEx(key, u"Microsoft", 0, KEY_ALL_ACCESS)
    assert hook.seen[0][0] == "winreg.CreateKey"
    assert hook.seen[0][1] == (HKEY_CURRENT_USER, u"SOFTWARE", KEY_WRITE)
    assert hook.seen[1][0] == "winreg.OpenKey/result"
    assert hook.seen[1][1] == (key.handle, )
    assert hook.seen[2][0] == "winreg.CreateKey"
    assert hook.seen[2][1] == (key.handle, u"Microsoft", KEY_ALL_ACCESS)
    assert hook.seen[3][0] == "winreg.OpenKey/result"
    assert hook.seen[3][1] == (sub_key.handle, )
    sub_key.Close()
    key.Close()

def test_ExpandEnvironmentStrings():
    from winreg import ExpandEnvironmentStrings
    s = u"This is a test string"
    with TestHook() as hook:
        ExpandEnvironmentStrings(s)
    assert hook.seen[0] == ("winreg.ExpandEnvironmentStrings", (s, ))

def test_LoadKey():
    from winreg import LoadKey, HKEY_USERS
    subkey = u"PyPy Test key - Delete me"
    filename = u"This is a long filename that doesn't exist, hopefully"
    with TestHook() as hook:
        try:
            LoadKey(HKEY_USERS, subkey, filename)
        except OSError:
            pass
    assert hook.seen[0] == ("winreg.LoadKey", (HKEY_USERS, subkey, filename))

def test_OpenKey():
    from winreg import OpenKey, OpenKeyEx
    from winreg import HKEY_CURRENT_USER, KEY_ALL_ACCESS, KEY_READ
    with TestHook() as hook:
        key = OpenKey(HKEY_CURRENT_USER, u"SOFTWARE")
        sub_key = OpenKeyEx(key, u"Microsoft", 0, KEY_ALL_ACCESS)
    assert hook.seen[0][0] == "winreg.OpenKey"
    assert hook.seen[0][1] == (HKEY_CURRENT_USER, u"SOFTWARE", KEY_READ)
    assert hook.seen[1][0] == "winreg.OpenKey/result"
    assert hook.seen[1][1] == (key.handle, )
    assert hook.seen[2][0] == "winreg.OpenKey"
    assert hook.seen[2][1] == (key.handle, u"Microsoft", KEY_ALL_ACCESS)
    assert hook.seen[3][0] == "winreg.OpenKey/result"
    assert hook.seen[3][1] == (sub_key.handle, )
    sub_key.Close()
    key.Close()

def test_PyHKEY_Detach():
    from winreg import OpenKey, CloseKey, HKEY_CURRENT_USER
    with TestHook() as hook:
        key = OpenKey(HKEY_CURRENT_USER, u"SOFTWARE")
        handle = key.Detach()
        CloseKey(handle)
    assert hook.seen[-1] == ("winreg.PyHKEY.Detach", (handle, ))

def test_QueryInfoKey():
    from winreg import QueryInfoKey, HKEY_CURRENT_USER
    with TestHook() as hook:
        QueryInfoKey(HKEY_CURRENT_USER)
    assert hook.seen[0] == ("winreg.QueryInfoKey", (HKEY_CURRENT_USER, ))

def test_QueryValue():
    from winreg import QueryValue, QueryValueEx, HKEY_CURRENT_USER
    with TestHook() as hook:
        QueryValue(HKEY_CURRENT_USER, u"SOFTWARE")
        try:
            QueryValueEx(HKEY_CURRENT_USER, u"Invalid")
        except OSError:
            pass
    assert hook.seen[0] == ("winreg.QueryValue", (HKEY_CURRENT_USER, u"SOFTWARE", None))
    assert hook.seen[1] == ("winreg.QueryValue", (HKEY_CURRENT_USER, None, u"Invalid"))

def test_SaveKey():
    from winreg import SaveKey, HKEY_CURRENT_USER
    filename = u"this file should not be created, delete me"
    with TestHook(raise_on_events="winreg.SaveKey") as hook:
        try:
            SaveKey(HKEY_CURRENT_USER, filename)
        except RuntimeError as ex:
            assert str(ex) == "saw event winreg.SaveKey"
        else:
            assert False
    assert hook.seen[0] == ("winreg.SaveKey", (HKEY_CURRENT_USER, filename))

def test_set_and_delete():
    import os
    from winreg import CreateKey, HKEY_CURRENT_USER, REG_SZ, KEY_WOW64_64KEY
    from winreg import DeleteKey, DeleteKeyEx, DeleteValue, SetValue, SetValueEx
    key_name = "SOFTWARE\\Pypy Test Key 2 - Delete Me [%d]" % os.getpid()
    subkey_name = "Test SubKey"
    subkey2_name = "Test SubKey 2"
    value_name = "Test Value"
    value = "hello world"
    with CreateKey(HKEY_CURRENT_USER, key_name) as key:
        handle = key.handle
        with TestHook() as hook:
            SetValue(key, subkey_name, REG_SZ, value)
            SetValueEx(key, value_name, 0, REG_SZ, value)
            DeleteValue(key, value_name)
            try:
                DeleteKeyEx(key, subkey2_name, KEY_WOW64_64KEY, 0)
            except (NotImplementedError, OSError):
                pass
            DeleteKey(key, subkey_name)
            DeleteKey(HKEY_CURRENT_USER, key_name)
    assert hook.seen[0] == ("winreg.SetValue", (handle, subkey_name, REG_SZ, value))
    assert hook.seen[1] == ("winreg.SetValue", (handle, value_name, REG_SZ, value))
    assert hook.seen[2] == ("winreg.DeleteValue", (handle, value_name))
    assert hook.seen[3] == ("winreg.DeleteKey", (handle, subkey2_name, KEY_WOW64_64KEY))
    assert hook.seen[4] == ("winreg.DeleteKey", (handle, subkey_name, 0))
    assert hook.seen[5] == ("winreg.DeleteKey", (HKEY_CURRENT_USER, key_name, 0))

def test_enum():
    from winreg import EnumKey, EnumValue, HKEY_CURRENT_USER
    functions = [
        (EnumKey, "winreg.EnumKey"),
        (EnumValue, "winreg.EnumValue"),
    ]
    index = 42
    with TestHook() as hook:
        for func, ev in functions:
            try:
                func(HKEY_CURRENT_USER, index)
            except OSError:
                pass
    for i, (func, ev) in enumerate(functions):
        assert hook.seen[i] == (ev, (HKEY_CURRENT_USER, index))

def test_reflection():
    from winreg import DisableReflectionKey, EnableReflectionKey, \
                       QueryReflectionKey, OpenKey, HKEY_LOCAL_MACHINE
    functions = [
        (DisableReflectionKey, "winreg.DisableReflectionKey"),
        (EnableReflectionKey, "winreg.EnableReflectionKey"),
        (QueryReflectionKey, "winreg.QueryReflectionKey"),
    ]
    # calling {Dis,En}ableReflectionKey on HKLM\Software has no effect in all OSes
    with OpenKey(HKEY_LOCAL_MACHINE, "Software") as key:
        with TestHook() as hook:
            for func, ev in functions:
                try:
                    func(key)
                except NotImplementedError:
                    pass
        for i, (func, ev) in enumerate(functions):
            assert hook.seen[i] == (ev, (key.handle, ))
