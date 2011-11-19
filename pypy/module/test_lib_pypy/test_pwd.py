import py, sys
from pypy.conftest import gettestobjspace

class AppTestPwd:
    def setup_class(cls):
        if sys.platform == 'win32':
            py.test.skip("Unix only")
        cls.space = gettestobjspace(usemodules=('_ffi', '_rawffi'))
        cls.space.appexec((), "(): import pwd")

    def test_getpwuid(self):
        import os, pwd
        passwd_info = pwd.getpwuid(os.getuid())
        assert type(passwd_info).__name__ == 'struct_passwd'
        assert repr(passwd_info).startswith("pwd.struct_passwd(pw_name=")
