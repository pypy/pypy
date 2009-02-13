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

    def test_setlocale(self):
        import _locale

        raises(TypeError, _locale.setlocale, "", "en_US")
        raises(TypeError, _locale.setlocale, _locale.LC_ALL, 6)
        raises(_locale.Error, _locale.setlocale, 123456, "en_US")

        assert _locale.setlocale(_locale.LC_ALL, None)
        assert _locale.setlocale(_locale.LC_ALL)

    def test_string_ulcase(self):
        import _locale, string

        lcase = "abcdefghijklmnopqrstuvwxyz"
        ucase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        _locale.setlocale(_locale.LC_ALL, "en_US.UTF-8")
        assert string.lowercase == lcase
        assert string.uppercase == ucase

        _locale.setlocale(_locale.LC_ALL, "en_US")
        assert string.lowercase != lcase
        assert string.uppercase != ucase

    def test_localeconv(self):
        skip("raise BytecodeCorruption - wtf?")
        import _locale

        lconv_c = {
            "currency_symbol": "",
            "decimal_point": ".",
            "frac_digits": 127,
            "grouping": [],
            "int_curr_symbol": "",
            "int_frac_digits": 127,
            "mon_decimal_point": "",
            "mon_grouping": [],
            "mon_thousands_sep": "",
            "n_cs_precedes": 127,
            "n_sep_by_space": 127,
            "n_sign_posn": 127,
            "negative_sign": "",
            "p_cs_precedes": 127,
            "p_sep_by_space": 127,
            "p_sign_posn": 127,
            "positive_sign": "",
            "thousands_sep": "" }

        _locale.setlocale(_locale.LC_ALL, "C")

        lconv = _locale.localeconv()
        for k, v in lconv_c.items():
            assert lconv[k] == v

    def test_str_float(self):
        import _locale
        import locale

        _locale.setlocale(_locale.LC_ALL, "en_US")
        assert locale.str(1.1) == '1.1'
        _locale.setlocale(_locale.LC_ALL, "pl_PL")
        assert locale.str(1.1) == '1,1'

