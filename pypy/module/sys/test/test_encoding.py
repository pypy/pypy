import os, py
from pypy.module.sys.interp_encoding import _getfilesystemencoding
from pypy.module.sys.interp_encoding import base_encoding


def test__getfilesystemencoding(space):
    assert _getfilesystemencoding(space) == base_encoding


def test__getfilesystemencoding_does_not_coerce_locale(space):
    """_getfilesystemencoding must not modify LC_CTYPE as a side effect.

    Previously it coerced LC_CTYPE from 'C'/'POSIX' to 'en_US.UTF-8', which
    caused app_main.py's POSIX locale detection (for utf8_mode) to miss the
    'C' locale and set utf8_mode=0 instead of 1.
    """
    from rpython.rlib import rlocale
    if not rlocale.HAVE_LANGINFO:
        py.test.skip("requires HAVE_LANGINFO")
    original = rlocale.setlocale(rlocale.LC_CTYPE, None)
    try:
        rlocale.setlocale(rlocale.LC_CTYPE, "C")
        _getfilesystemencoding(space)
        assert rlocale.setlocale(rlocale.LC_CTYPE, None) == "C"
    finally:
        rlocale.setlocale(rlocale.LC_CTYPE, original)
