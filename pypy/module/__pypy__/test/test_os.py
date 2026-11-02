class AppTestOs:
    spaceconfig = dict(usemodules=['__pypy__'])

    def setup_class(cls):
        cls.w_runappdirect = cls.space.wrap(cls.runappdirect)

    def test_real_getenv(self):
        import sys
        import __pypy__.os
        import os

        if sys.platform == 'win32' and not self.runappdirect:
            # untranslated, os.environ is the host's dict, but the win32
            # posix.putenv writes the CRT environment directly
            skip("only relevant for translated tests on win32")

        key = 'UNLIKELY_SET'
        assert key not in os.environ
        os.putenv(key, '42')
        # this one skips Python cache
        assert __pypy__.os.real_getenv(key) == '42'
        # this one can only see things set on interpter start (cached)
        assert os.getenv(key) is None
        os.unsetenv(key)
        assert __pypy__.os.real_getenv(key) is None
