
# -*- coding: utf-8 -*-

import py
import locale as cpython_locale
from pypy.rlib.rlocale import setlocale, LC_ALL, LocaleError

class TestLocale(object):
    def setup_class(cls):
        try:
            cls.oldlocale = setlocale(LC_ALL, "pl_PL.utf8")
        except LocaleError:
            py.test.skip("polish locale unsupported")

    def teardown_class(cls):
        setlocale(LC_ALL, cls.oldlocale)

    def test_setlocale(self):
        assert u"Ą".isupper()
