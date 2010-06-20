
# -*- coding: utf-8 -*-

import py
import locale as cpython_locale
from pypy.rlib.rlocale import setlocale, LC_ALL, LocaleError, isupper, \
     islower, isalpha, tolower, isalnum, numeric_formatting

class TestLocale(object):
    def setup_class(cls):
        try:
            cls.oldlocale = setlocale(LC_ALL, "pl_PL.utf8")
        except LocaleError:
            py.test.skip("polish locale unsupported")

    def teardown_class(cls):
        if hasattr(cls, "oldlocale"):
            setlocale(LC_ALL, cls.oldlocale)

    def test_setlocale_worked(self):
        assert u"Ą".isupper()
        raises(LocaleError, setlocale, LC_ALL, "bla bla bla")
        raises(LocaleError, setlocale, 1234455, None)

    def test_lower_upper(self):
        assert isupper(ord("A"))
        assert islower(ord("a"))
        assert not isalpha(ord(" "))
        assert isalnum(ord("1"))
        assert tolower(ord("A")) == ord("a")

def test_numeric_formatting():
    dec, th, grouping = numeric_formatting()
    assert isinstance(dec, str)
    assert isinstance(th, str)
    assert isinstance(grouping, str)
