from pypy.conftest import gettestobjspace

import sys

class AppTestLocaleTrivia:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_locale'])

        #cls.w_locale = cls.space.appexec([], """():
        #    import locale
        #    return locale""")

    def test_import(self):
        import _locale
        assert _locale

        import locale
        assert locale

    def test_contants(self):
        _CONSTANTS = (
            'LC_CTYPE',
            'LC_NUMERIC',
            'LC_TIME',
            'LC_COLLATE',
            'LC_MONETARY',
            'LC_MESSAGES',
            'LC_ALL',
            'LC_PAPER',
            'LC_NAME',
            'LC_ADDRESS',
            'LC_TELEPHONE',
            'LC_MEASUREMENT',
            'LC_IDENTIFICATION',
        )

        import _locale
        
        for constant in _CONSTANTS:
            assert hasattr(_locale, constant)

    def test_str_float(self):
        skip("in progress")
        import locale

        locale.setlocale(locale.LC_ALL, "en_US")
        assert locale.str(1.1) == '1.1'
        locale.setlocale(locale.LC_ALL, "pl_PL")
        assert locale.str(1.1) == '1,1'

