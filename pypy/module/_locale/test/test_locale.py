import py
from pypy.conftest import gettestobjspace

import sys

class AppTestLocaleTrivia:
    def setup_class(cls):
        cls.space = space = gettestobjspace(usemodules=['_locale'])
        if sys.platform != 'win32':
            cls.w_language_en = cls.space.wrap("en_US")
            cls.w_language_utf8 = cls.space.wrap("en_US.UTF-8")
            cls.w_language_pl = cls.space.wrap("pl_PL.UTF-8")
            cls.w_encoding_pl = cls.space.wrap("utf-8")
        else:
            cls.w_language_en = cls.space.wrap("English_US")
            cls.w_language_utf8 = cls.space.wrap("English_US.65001")
            cls.w_language_pl = cls.space.wrap("Polish_Poland.1257")
            cls.w_encoding_pl = cls.space.wrap("cp1257")
        import _locale
        # check whether used locales are installed, otherwise the tests will
        # fail
        current = _locale.setlocale(_locale.LC_ALL)
        try:
            try:
                _locale.setlocale(_locale.LC_ALL,
                                  space.str_w(cls.w_language_en))
                _locale.setlocale(_locale.LC_ALL,
                                  space.str_w(cls.w_language_pl))
            except _locale.Error:
                py.test.skip("necessary locales not installed")

            # Windows forbids the UTF-8 character set since Windows XP.
            try:
                _locale.setlocale(_locale.LC_ALL,
                                  space.str_w(cls.w_language_utf8))
            except _locale.Error:
                del cls.w_language_utf8
        finally:
            _locale.setlocale(_locale.LC_ALL, current)

    def test_import(self):
        import _locale
        assert _locale

        import locale
        assert locale
        
    def test_constants(self):
        import sys

        _CONSTANTS = (
            'LC_CTYPE',
            'LC_NUMERIC',
            'LC_TIME',
            'LC_COLLATE',
            'LC_MONETARY',
            'LC_ALL',
            'CHAR_MAX',

            # These are optional
            #'LC_MESSAGES',
            #'LC_PAPER',
            #'LC_NAME',
            #'LC_ADDRESS',
            #'LC_TELEPHONE',
            #'LC_MEASUREMENT',
            #'LC_IDENTIFICATION',
        )

        import _locale
        
        for constant in _CONSTANTS:
            assert hasattr(_locale, constant)


        # HAVE_LANGINFO
        if sys.platform != 'win32':
            _LANGINFO_NAMES = ('RADIXCHAR THOUSEP CRNCYSTR D_T_FMT D_FMT '
                        'T_FMT AM_STR PM_STR CODESET T_FMT_AMPM ERA ERA_D_FMT '
                        'ERA_D_T_FMT ERA_T_FMT ALT_DIGITS YESEXPR NOEXPR '
                        '_DATE_FMT').split()
            for i in range(1, 8):
                _LANGINFO_NAMES.append("DAY_%d" % i)
                _LANGINFO_NAMES.append("ABDAY_%d" % i)
            for i in range(1, 13):
                _LANGINFO_NAMES.append("MON_%d" % i)
                _LANGINFO_NAMES.append("ABMON_%d" % i)

            for constant in _LANGINFO_NAMES:
                assert hasattr(_locale, constant)

    def test_setlocale(self):
        import _locale

        raises(TypeError, _locale.setlocale, "", self.language_en)
        raises(TypeError, _locale.setlocale, _locale.LC_ALL, 6)
        raises(_locale.Error, _locale.setlocale, 123456, self.language_en)

        assert _locale.setlocale(_locale.LC_ALL, None)
        assert _locale.setlocale(_locale.LC_ALL)

    def test_string_ulcase(self):
        if not hasattr(self, 'language_utf8'):
            skip("No utf8 locale on this platform")
        import _locale, string

        lcase = "abcdefghijklmnopqrstuvwxyz"
        ucase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        _locale.setlocale(_locale.LC_ALL, self.language_utf8)
        assert string.lowercase == lcase
        assert string.uppercase == ucase

        _locale.setlocale(_locale.LC_ALL, self.language_en)

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

        _locale.setlocale(_locale.LC_ALL, self.language_pl)
        assert _locale.strcoll("a", "b") < 0
        assert _locale.strcoll(
            u"\N{LATIN SMALL LETTER A WITH OGONEK}".encode(self.encoding_pl),
            "b") < 0

        assert _locale.strcoll(
            u"\N{LATIN SMALL LETTER C WITH ACUTE}".encode(self.encoding_pl),
            "b") > 0
        assert _locale.strcoll("c", "b") > 0

        assert _locale.strcoll("b", "b") == 0

        raises(TypeError, _locale.strcoll, 1, "b")
        raises(TypeError, _locale.strcoll, "b", 1)

    def test_strcoll_unicode(self):
        import _locale

        _locale.setlocale(_locale.LC_ALL, self.language_pl)
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

        _locale.setlocale(_locale.LC_ALL, self.language_pl)
        a = "1234"
        b = _locale.strxfrm(a)
        assert a is not b

    def test_str_float(self):
        import _locale
        import locale

        _locale.setlocale(_locale.LC_ALL, self.language_en)
        assert locale.str(1.1) == '1.1'
        _locale.setlocale(_locale.LC_ALL, self.language_pl)
        assert locale.str(1.1) == '1,1'

    def test_text(self):
        import sys
        if sys.platform == 'win32':
            skip("No gettext on Windows")

        # TODO more tests would be nice
        import _locale

        assert _locale.gettext("1234") == "1234"
        assert _locale.dgettext(None, "1234") == "1234"
        assert _locale.dcgettext(None, "1234", _locale.LC_MESSAGES) == "1234"
        assert _locale.textdomain("1234") == "1234"

    def test_nl_langinfo(self):
        import sys
        if sys.platform == 'win32':
            skip("No langinfo on Windows")

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
        import sys
        if sys.platform == 'win32':
            skip("No textdomain on Windows")

        # TODO more tests would be nice
        import _locale

        raises(OSError, _locale.bindtextdomain, '', '')
        raises(OSError, _locale.bindtextdomain, '', '1')

    def test_bind_textdomain_codeset(self):
        import sys
        if sys.platform == 'win32':
            skip("No textdomain on Windows")

        import _locale

        assert _locale.bind_textdomain_codeset('/', None) is None
        assert _locale.bind_textdomain_codeset('/', 'UTF-8') == 'UTF-8'
        assert _locale.bind_textdomain_codeset('/', None) == 'UTF-8'

        assert _locale.bind_textdomain_codeset('', '') is None

    def test_getdefaultlocale(self):
        import sys
        if sys.platform != 'win32':
            skip("No _getdefaultlocale() to test")

        import _locale
        lang, encoding = _locale._getdefaultlocale()
        assert lang is None or isinstance(lang, str)
        assert encoding.startswith('cp')

