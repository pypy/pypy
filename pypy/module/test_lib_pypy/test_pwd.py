import py, sys

class AppTestPwd:
    spaceconfig = dict(usemodules=('_rawffi', 'itertools', 'binascii'))

    def setup_class(cls):
        if sys.platform == 'win32':
            py.test.skip("Unix only")
        cls.space.appexec((), "(): import pwd")

    def test_getpwuid(self):
        import os, pwd
        passwd_info = pwd.getpwuid(os.getuid())
        assert type(passwd_info).__name__ == 'struct_passwd'
        assert repr(passwd_info).startswith("pwd.struct_passwd(pw_name=")
