# ctypes implementation of _locale module by Victor Stinner, 2008-03-27
"""
Support for POSIX locales.
"""

from ctypes import (Structure, POINTER, create_string_buffer,
    c_ubyte, c_int, c_char_p, c_wchar_p)
from ctypes_support import standard_c_lib as libc
from ctypes_support import get_errno

# load the platform-specific cache made by running locale.ctc.py
from ctypes_config_cache._locale_cache import *


size_t = c_int


# Ubuntu Gusty i386 structure
class lconv(Structure):
    _fields_ = (
        # Numeric (non-monetary) information.
        ("decimal_point", c_char_p),    # Decimal point character.
        ("thousands_sep", c_char_p),    # Thousands separator.

        # Each element is the number of digits in each group;
        # elements with higher indices are farther left.
        # An element with value CHAR_MAX means that no further grouping is done.
        # An element with value 0 means that the previous element is used
        # for all groups farther left.  */
        ("grouping", c_char_p),

        # Monetary information.

        # First three chars are a currency symbol from ISO 4217.
        # Fourth char is the separator.  Fifth char is '\0'.
        ("int_curr_symbol", c_char_p),
        ("currency_symbol", c_char_p),   # Local currency symbol.
        ("mon_decimal_point", c_char_p), # Decimal point character.
        ("mon_thousands_sep", c_char_p), # Thousands separator.
        ("mon_grouping", c_char_p),      # Like `grouping' element (above).
        ("positive_sign", c_char_p),     # Sign for positive values.
        ("negative_sign", c_char_p),     # Sign for negative values.
        ("int_frac_digits", c_ubyte),    # Int'l fractional digits.
        ("frac_digits", c_ubyte),        # Local fractional digits.
        # 1 if currency_symbol precedes a positive value, 0 if succeeds.
        ("p_cs_precedes", c_ubyte),
        # 1 iff a space separates currency_symbol from a positive value.
        ("p_sep_by_space", c_ubyte),
        # 1 if currency_symbol precedes a negative value, 0 if succeeds.
        ("n_cs_precedes", c_ubyte),
        # 1 iff a space separates currency_symbol from a negative value.
        ("n_sep_by_space", c_ubyte),

        # Positive and negative sign positions:
        # 0 Parentheses surround the quantity and currency_symbol.
        # 1 The sign string precedes the quantity and currency_symbol.
        # 2 The sign string follows the quantity and currency_symbol.
        # 3 The sign string immediately precedes the currency_symbol.
        # 4 The sign string immediately follows the currency_symbol.
        ("p_sign_posn", c_ubyte),
        ("n_sign_posn", c_ubyte),
        # 1 if int_curr_symbol precedes a positive value, 0 if succeeds.
        ("int_p_cs_precedes", c_ubyte),
        # 1 iff a space separates int_curr_symbol from a positive value.
        ("int_p_sep_by_space", c_ubyte),
        # 1 if int_curr_symbol precedes a negative value, 0 if succeeds.
        ("int_n_cs_precedes", c_ubyte),
        # 1 iff a space separates int_curr_symbol from a negative value.
        ("int_n_sep_by_space", c_ubyte),
         # Positive and negative sign positions:
         # 0 Parentheses surround the quantity and int_curr_symbol.
         # 1 The sign string precedes the quantity and int_curr_symbol.
         # 2 The sign string follows the quantity and int_curr_symbol.
         # 3 The sign string immediately precedes the int_curr_symbol.
         # 4 The sign string immediately follows the int_curr_symbol.
        ("int_p_sign_posn", c_ubyte),
        ("int_n_sign_posn", c_ubyte),
    )

_setlocale = libc.setlocale
_setlocale.argtypes = (c_int, c_char_p)
_setlocale.restype = c_char_p

_localeconv = libc.localeconv
_localeconv.argtypes = None
_localeconv.restype = POINTER(lconv)

_strcoll = libc.strcoll
_strcoll.argtypes = (c_char_p, c_char_p)
_strcoll.restype = c_int

_wcscoll = libc.wcscoll
_wcscoll.argtypes = (c_wchar_p, c_wchar_p)
_wcscoll.restype = c_int

_strxfrm = libc.strxfrm
_strxfrm.argtypes = (c_char_p, c_char_p, size_t)
_strxfrm.restype = size_t

HAS_LIBINTL = hasattr(libc, 'gettext')
if HAS_LIBINTL:
    _gettext = libc.gettext
    _gettext.argtypes = (c_char_p,)
    _gettext.restype = c_char_p

    _dgettext = libc.dgettext
    _dgettext.argtypes = (c_char_p, c_char_p)
    _dgettext.restype = c_char_p

    _dcgettext = libc.dcgettext
    _dcgettext.argtypes = (c_char_p, c_char_p, c_int)
    _dcgettext.restype = c_char_p

    _textdomain = libc.textdomain
    _textdomain.argtypes = (c_char_p,)
    _textdomain.restype = c_char_p

    _bindtextdomain = libc.bindtextdomain
    _bindtextdomain.argtypes = (c_char_p, c_char_p)
    _bindtextdomain.restype = c_char_p

    HAS_BIND_TEXTDOMAIN_CODESET = hasattr(libc, 'bindtextdomain_codeset')
    if HAS_BIND_TEXTDOMAIN_CODESET:
        _bind_textdomain_codeset = libc.bindtextdomain_codeset
        _bind_textdomain_codeset.argtypes = (c_char_p, c_char_p)
        _bind_textdomain_codeset.restype = c_char_p

class Error(Exception):
    pass

def fixup_ulcase():
    import string
    #import strop

    # create uppercase map string
    ul = []
    for c in xrange(256):
        c = chr(c)
        if c.isupper():
            ul.append(c)
    ul = ''.join(ul)
    string.uppercase = ul
    #strop.uppercase = ul

    # create lowercase string
    ul = []
    for c in xrange(256):
        c = chr(c)
        if c.islower():
            ul.append(c)
    ul = ''.join(ul)
    string.lowercase = ul
    #strop.lowercase = ul

    # create letters string
    ul = []
    for c in xrange(256):
        c = chr(c)
        if c.isalpha():
            ul.append(c)
    ul = ''.join(ul)
    string.letters = ul

def setlocale(category, locale=None):
    "(integer,string=None) -> string. Activates/queries locale processing."
    if locale:
        # set locale
        result = _setlocale(category, locale)
        if not result:
            raise Error("unsupported locale setting")

        # record changes to LC_CTYPE
        if category in (LC_CTYPE, LC_ALL):
            fixup_ulcase()
    else:
        # get locale
        result = _setlocale(category, None)
        if not result:
            raise Error("locale query failed")
    return result

def _copy_grouping(text):
    groups = [ ord(group) for group in text ]
    if groups:
        groups.append(0)
    return groups

def localeconv():
    "() -> dict. Returns numeric and monetary locale-specific parameters."

    # if LC_NUMERIC is different in the C library, use saved value
    lp = _localeconv()
    l = lp.contents

    # hopefully, the localeconv result survives the C library calls
    # involved herein

    # Numeric information
    result = {
        "decimal_point": l.decimal_point,
        "thousands_sep": l.thousands_sep,
        "grouping": _copy_grouping(l.grouping),
        "int_curr_symbol": l.int_curr_symbol,
        "currency_symbol": l.currency_symbol,
        "mon_decimal_point": l.mon_decimal_point,
        "mon_thousands_sep": l.mon_thousands_sep,
        "mon_grouping": _copy_grouping(l.mon_grouping),
        "positive_sign": l.positive_sign,
        "negative_sign": l.negative_sign,
        "int_frac_digits": l.int_frac_digits,
        "frac_digits": l.frac_digits,
        "p_cs_precedes": l.p_cs_precedes,
        "p_sep_by_space": l.p_sep_by_space,
        "n_cs_precedes": l.n_cs_precedes,
        "n_sep_by_space": l.n_sep_by_space,
        "p_sign_posn": l.p_sign_posn,
        "n_sign_posn": l.n_sign_posn,
    }
    return result

def strcoll(s1, s2):
    "string,string -> int. Compares two strings according to the locale."

    # If both arguments are byte strings, use strcoll.
    if isinstance(s1, str) and isinstance(s2, str):
        return _strcoll(s1, s2)

    # If neither argument is unicode, it's an error.
    if not isinstance(s1, unicode) and not isinstance(s2, unicode):
        raise ValueError("strcoll arguments must be strings")

    # Convert the non-unicode argument to unicode.
    s1 = unicode(s1)
    s2 = unicode(s2)

    # Collate the strings.
    return _wcscoll(s1, s2)

def strxfrm(s):
    "string -> string. Returns a string that behaves for cmp locale-aware."

    # assume no change in size, first
    n1 = len(s) + 1
    buf = create_string_buffer(n1)
    n2 = _strxfrm(buf, s, n1) + 1
    if n2 > n1:
        # more space needed
        buf = create_string_buffer(n2)
        _strxfrm(buf, s, n2)
    return buf.value

def getdefaultlocale():
    # TODO: Port code from CPython for Windows and Mac OS
    raise NotImplementedError()

if HAS_LANGINFO:
    _nl_langinfo = libc.nl_langinfo
    _nl_langinfo.argtypes = (nl_item,)
    _nl_langinfo.restype = c_char_p

    def nl_langinfo(key):
        """nl_langinfo(key) -> string
        Return the value for the locale information associated with key."""
        # Check whether this is a supported constant. GNU libc sometimes
        # returns numeric values in the char* return value, which would
        # crash PyString_FromString.
        result = _nl_langinfo(key)
        if result is not None:
            return result
        raise ValueError("unsupported langinfo constant")

if HAS_LIBINTL:
    def gettext(msg):
        """gettext(msg) -> string
        Return translation of msg."""
        return _gettext(msg)

    def dgettext(domain, msg):
        """dgettext(domain, msg) -> string
        Return translation of msg in domain."""
        return _dgettext(domain, msg)

    def dcgettext(domain, msg, category):
        """dcgettext(domain, msg, category) -> string
        Return translation of msg in domain and category."""
        return _dcgettext(domain, msg, category)

    def textdomain(domain):
        """textdomain(domain) -> string
        Set the C library's textdomain to domain, returning the new domain."""
        return _textdomain(domain)

    def bindtextdomain(domain, dir):
        """bindtextdomain(domain, dir) -> string
        Bind the C library's domain to dir."""
        dirname = _bindtextdomain(domain, dir)
        if not dirname:
            errno = get_errno()
            raise OSError(errno)
        return dirname

    if HAS_BIND_TEXTDOMAIN_CODESET:
        def bind_textdomain_codeset(domain, codeset):
            """bind_textdomain_codeset(domain, codeset) -> string
            Bind the C library's domain to codeset."""
            codeset = _bind_textdomain_codeset(domain, codeset)
            if codeset:
                return codeset
            return None

__all__ = (
    'Error',
    'setlocale', 'localeconv', 'strxfrm', 'strcoll',
) + ALL_CONSTANTS
if HAS_LIBINTL:
    __all__ += ('gettext', 'dgettext', 'dcgettext', 'textdomain',
                'bindtextdomain')
    if HAS_BIND_TEXTDOMAIN_CODESET:
        __all__ += ('bind_textdomain_codeset',)
if HAS_LANGINFO:
    __all__ += ('nl_langinfo',)
