# -*- coding: utf-8 -*-
from pypy.conftest import gettestobjspace

import sys

class AppTestLocaleTrivia:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_locale'])

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
            'CHAR_MAX',
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

    def test_strcoll(self):
        import _locale

        _locale.setlocale(_locale.LC_ALL, "pl_PL.UTF-8")
        assert _locale.strcoll("a", "b") < 0
        assert _locale.strcoll("ą", "b") < 0

        assert _locale.strcoll("ć", "b") > 0
        assert _locale.strcoll("c", "b") > 0

        assert _locale.strcoll("b", "b") == 0

        raises(TypeError, _locale.strcoll, 1, "b")
        raises(TypeError, _locale.strcoll, "b", 1)

    def test_strcoll_unicode(self):
        import _locale

        _locale.setlocale(_locale.LC_ALL, "pl_PL.UTF-8")
        assert _locale.strcoll(u"b", u"b") == 0
        assert _locale.strcoll(u"a", u"b") < 0
        assert _locale.strcoll(u"b", u"a") > 0

        raises(TypeError, _locale.strcoll, 1, u"b")
        raises(TypeError, _locale.strcoll, u"b", 1)

    def test_strxfrm(self):
        # TODO more tests would be nice
        import _locale

        _locale.setlocale(_locale.LC_ALL, "C")
        a = "1234"
        b = _locale.strxfrm(a)
        assert a is not b
        assert a == b

        raises(TypeError, _locale.strxfrm, 1)

        _locale.setlocale(_locale.LC_ALL, "pl_PL.UTF-8")
        a = "1234"
        b = _locale.strxfrm(a)
        assert a is not b

    def test_str_float(self):
        import _locale
        import locale

        _locale.setlocale(_locale.LC_ALL, "en_US.UTF-8")
        assert locale.str(1.1) == '1.1'
        _locale.setlocale(_locale.LC_ALL, "pl_PL.UTF-8")
        assert locale.str(1.1) == '1,1'

    def test_text(self):
        # TODO more tests would be nice
        import _locale

        assert _locale.gettext("1234") == "1234"
        assert _locale.dgettext(None, "1234") == "1234"
        assert _locale.dcgettext(None, "1234", _locale.LC_MESSAGES) == "1234"
        assert _locale.textdomain("1234") == "1234"

    def test_nl_langinfo(self):
        import _locale

        langinfo_consts = [
                            'ABDAY_1',
                            'ABDAY_2',
                            'ABDAY_3',
                            'ABDAY_4',
                            'ABDAY_5',
                            'ABDAY_6',
                            'ABDAY_7',
                            'ABMON_1',
                            'ABMON_10',
                            'ABMON_11',
                            'ABMON_12',
                            'ABMON_2',
                            'ABMON_3',
                            'ABMON_4',
                            'ABMON_5',
                            'ABMON_6',
                            'ABMON_7',
                            'ABMON_8',
                            'ABMON_9',
                            'CODESET',
                            'CRNCYSTR',
                            'DAY_1',
                            'DAY_2',
                            'DAY_3',
                            'DAY_4',
                            'DAY_5',
                            'DAY_6',
                            'DAY_7',
                            'D_FMT',
                            'D_T_FMT',
                            'MON_1',
                            'MON_10',
                            'MON_11',
                            'MON_12',
                            'MON_2',
                            'MON_3',
                            'MON_4',
                            'MON_5',
                            'MON_6',
                            'MON_7',
                            'MON_8',
                            'MON_9',
                            'NOEXPR',
                            'RADIXCHAR',
                            'THOUSEP',
                            'T_FMT',
                            'YESEXPR',
                            'AM_STR',
                            'PM_STR',
                            ]
        for constant in langinfo_consts:
            assert hasattr(_locale, constant)

        _locale.setlocale(_locale.LC_ALL, "C")
        assert _locale.nl_langinfo(_locale.ABDAY_1) == "Sun"
        assert _locale.nl_langinfo(_locale.ABMON_1) == "Jan"
        assert _locale.nl_langinfo(_locale.T_FMT) == "%H:%M:%S"
        assert _locale.nl_langinfo(_locale.YESEXPR) == '^[yY]'
        assert _locale.nl_langinfo(_locale.NOEXPR) == "^[nN]"
        assert _locale.nl_langinfo(_locale.THOUSEP) == ''

        raises(ValueError, _locale.nl_langinfo, 12345)
        raises(TypeError, _locale.nl_langinfo, None)
    
    def test_bindtextdomain(self):
        # TODO more tests would be nice
        import _locale

        raises(OSError, _locale.bindtextdomain, '', '')
        raises(OSError, _locale.bindtextdomain, '', '1')

    def test_bind_textdomain_codeset(self):
        import _locale

        assert _locale.bind_textdomain_codeset('/', None) is None
        assert _locale.bind_textdomain_codeset('/', 'UTF-8') == 'UTF-8'
        assert _locale.bind_textdomain_codeset('/', None) == 'UTF-8'

        assert _locale.bind_textdomain_codeset('', '') is None
