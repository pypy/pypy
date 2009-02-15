from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import rposix

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root

from pypy.translator.tool.cbuild import ExternalCompilationInfo

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = ['locale.h', 'langinfo.h', 'limits.h']
    )
    lconv = platform.Struct("struct lconv", [
            # Numeric (non-monetary) information.
            ("decimal_point", rffi.CCHARP),    # Decimal point character.
            ("thousands_sep", rffi.CCHARP),    # Thousands separator.

            ## Each element is the number of digits in each group;
            ## elements with higher indices are farther left.
            ## An element with value CHAR_MAX means that no further grouping is done.
            ## An element with value 0 means that the previous element is used
            ## for all groups farther left.  */
            ("grouping", rffi.CCHARP),

            ## Monetary information.

            ## First three chars are a currency symbol from ISO 4217.
            ## Fourth char is the separator.  Fifth char is '\0'.
            ("int_curr_symbol", rffi.CCHARP),
            ("currency_symbol", rffi.CCHARP),   # Local currency symbol.
            ("mon_decimal_point", rffi.CCHARP), # Decimal point character.
            ("mon_thousands_sep", rffi.CCHARP), # Thousands separator.
            ("mon_grouping", rffi.CCHARP),      # Like `grouping' element (above).
            ("positive_sign", rffi.CCHARP),     # Sign for positive values.
            ("negative_sign", rffi.CCHARP),     # Sign for negative values.
            ("int_frac_digits", rffi.UCHAR),    # Int'l fractional digits.

            ("frac_digits", rffi.UCHAR),        # Local fractional digits.
            ## 1 if currency_symbol precedes a positive value, 0 if succeeds.
            ("p_cs_precedes", rffi.UCHAR),
            ## 1 iff a space separates currency_symbol from a positive value.
            ("p_sep_by_space", rffi.UCHAR),
            ## 1 if currency_symbol precedes a negative value, 0 if succeeds.
            ("n_cs_precedes", rffi.UCHAR),
            ## 1 iff a space separates currency_symbol from a negative value.
            ("n_sep_by_space", rffi.UCHAR),

            ## Positive and negative sign positions:
            ## 0 Parentheses surround the quantity and currency_symbol.
            ## 1 The sign string precedes the quantity and currency_symbol.
            ## 2 The sign string follows the quantity and currency_symbol.
            ## 3 The sign string immediately precedes the currency_symbol.
            ## 4 The sign string immediately follows the currency_symbol.
            ("p_sign_posn", rffi.UCHAR),
            ("n_sign_posn", rffi.UCHAR),
            ])


constants = {}
constant_names = (
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
        # from limits.h
        'CHAR_MAX',
        )

for name in constant_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))


langinfo_names = ('CODESET D_T_FMT D_FMT T_FMT RADIXCHAR THOUSEP '
                  'YESEXPR NOEXPR CRNCYSTR AM_STR PM_STR').split(" ")
for i in range(1, 8):
    langinfo_names.append("DAY_%d" % i)
    langinfo_names.append("ABDAY_%d" % i)
for i in range(1, 13):
    langinfo_names.append("MON_%d" % i)
    langinfo_names.append("ABMON_%d" % i)

for name in langinfo_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

class cConfig(object):
    pass

for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)

# needed to export the constants inside and outside. see __init__.py
for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value

for name in langinfo_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value

locals().update(constants)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=CConfig._compilation_info_)

def make_error(space, msg):
    w_module = space.getbuiltinmodule('_locale')
    w_exception_class = space.getattr(w_module, space.wrap('Error'))
    w_exception = space.call_function(w_exception_class, space.wrap(msg))
    return OperationError(w_exception_class, w_exception)

_setlocale = external('setlocale', [rffi.INT, rffi.CCHARP], rffi.CCHARP)

def setlocale(space, category, w_locale=None):
    "(integer,string=None) -> string. Activates/queries locale processing."

    if space.is_w(w_locale, space.w_None) or w_locale is None:
        result = _setlocale(rffi.cast(rffi.INT, category), None)
        if not result:
            raise make_error(space, "locale query failed")
    else:
        locale = rffi.str2charp(space.str_w(w_locale))

        result = _setlocale(rffi.cast(rffi.INT, category), locale)
        if not result:
            raise make_error(space, "unsupported locale setting")

        # record changes to LC_CTYPE
        if category in (LC_CTYPE, LC_ALL):
            w_module = space.getbuiltinmodule('_locale')
            w_fun = space.getattr(w_module, space.wrap('_fixup_ulcase'))
            space.call_function(w_fun)

    return space.wrap(rffi.charp2str(result))

setlocale.unwrap_spec = [ObjSpace, int, W_Root]

_lconv = lltype.Ptr(cConfig.lconv)
_localeconv = external('localeconv', [], _lconv)

def _copy_grouping(text):
    groups = [ ord(group) for group in text ]
    if groups:
        groups.append(0)
    return groups

def localeconv(space):
    "() -> dict. Returns numeric and monetary locale-specific parameters."
    lp = _localeconv()

    # Numeric information
    result = {
        "decimal_point": rffi.charp2str(lp.c_decimal_point),
        "thousands_sep": rffi.charp2str(lp.c_thousands_sep),
        "grouping": _copy_grouping(rffi.charp2str(lp.c_grouping)),
        "int_curr_symbol": rffi.charp2str(lp.c_int_curr_symbol),
        "currency_symbol": rffi.charp2str(lp.c_currency_symbol),
        "mon_decimal_point": rffi.charp2str(lp.c_mon_decimal_point),
        "mon_thousands_sep": rffi.charp2str(lp.c_mon_thousands_sep),
        "mon_grouping": _copy_grouping(rffi.charp2str(lp.c_mon_grouping)),
        "positive_sign": rffi.charp2str(lp.c_positive_sign),
        "negative_sign": rffi.charp2str(lp.c_negative_sign),
        "int_frac_digits": lp.c_int_frac_digits,
        "frac_digits": lp.c_frac_digits,
        "p_cs_precedes": lp.c_p_cs_precedes,
        "p_sep_by_space": lp.c_p_sep_by_space,
        "n_cs_precedes": lp.c_n_cs_precedes,
        "n_sep_by_space": lp.c_n_sep_by_space,
        "p_sign_posn": lp.c_p_sign_posn,
        "n_sign_posn": lp.c_n_sign_posn,
    }
    return space.wrap(result)

localeconv.unwrap_spec = [ObjSpace]

_strcoll = external('strcoll', [rffi.CCHARP, rffi.CCHARP], rffi.INT)
_wcscoll = external('wcscoll', [rffi.CWCHARP, rffi.CWCHARP], rffi.INT)

def strcoll(space, w_s1, w_s2):
    "string,string -> int. Compares two strings according to the locale."

    if space.is_true(space.isinstance(w_s1, space.w_str)) and \
       space.is_true(space.isinstance(w_s2, space.w_str)):

        s1, s2 = space.str_w(w_s1), space.str_w(w_s2)
        return space.wrap(_strcoll(rffi.str2charp(s1), rffi.str2charp(s2)))

    #if not space.is_true(space.isinstance(w_s1, space.w_unicode)) and \
    #   not space.is_true(space.isinstance(w_s2, space.w_unicode)):
    #    raise OperationError(space.w_ValueError,
    #                         space.wrap("strcoll arguments must be strings"))

    s1, s2 = space.unicode_w(w_s1), space.unicode_w(w_s2)

    s1_c = rffi.unicode2wcharp(s1)
    s2_c = rffi.unicode2wcharp(s2)
    result = _wcscoll(s1_c, s2_c)
    return space.wrap(result)

strcoll.unwrap_spec = [ObjSpace, W_Root, W_Root]

_strxfrm = external('strxfrm', [rffi.CCHARP, rffi.CCHARP, rffi.SIZE_T],
                                                                rffi.SIZE_T)

def strxfrm(space, s):
    "string -> string. Returns a string that behaves for cmp locale-aware."
    n1 = len(s) + 1

    buf = lltype.malloc(rffi.CCHARP.TO, n1, flavor="raw", zero=True)
    n2 = _strxfrm(buf, rffi.str2charp(s), n1) + 1
    if n2 > n1:
        # more space needed
        lltype.free(buf, flavor="raw")
        buf = lltype.malloc(rffi.CCHARP.TO, int(n2), flavor="raw", zero=True)
        _strxfrm(buf, rffi.str2charp(s), n2)

    val = rffi.charp2str(buf)
    lltype.free(buf, flavor="raw")

    return space.wrap(val)

strxfrm.unwrap_spec = [ObjSpace, str]

_gettext = external('gettext', [rffi.CCHARP], rffi.CCHARP)

def gettext(space, msg):
    """gettext(msg) -> string
    Return translation of msg."""
    return space.wrap(rffi.charp2str(_gettext(rffi.str2charp(msg))))

gettext.unwrap_spec = [ObjSpace, str]

_dgettext = external('dgettext', [rffi.CCHARP, rffi.CCHARP], rffi.CCHARP)

def dgettext(space, w_domain, msg):
    """dgettext(domain, msg) -> string
    Return translation of msg in domain."""
    if space.is_w(w_domain, space.w_None):
        domain = None
        result = _dgettext(domain, rffi.str2charp(msg))
    else:
        domain = space.str_w(w_domain)
        result = _dgettext(rffi.str2charp(domain), rffi.str2charp(msg))

    return space.wrap(rffi.charp2str(result))

dgettext.unwrap_spec = [ObjSpace, W_Root, str]

_dcgettext = external('dcgettext', [rffi.CCHARP, rffi.CCHARP, rffi.INT],
                                                                rffi.CCHARP)

def dcgettext(space, w_domain, msg, category):
    """dcgettext(domain, msg, category) -> string
    Return translation of msg in domain and category."""

    if space.is_w(w_domain, space.w_None):
        domain = None
        result = _dcgettext(domain, rffi.str2charp(msg),
                            rffi.cast(rffi.INT, category))
    else:
        domain = space.str_w(w_domain)
        result = _dcgettext(rffi.str2charp(domain), rffi.str2charp(msg),
                            rffi.cast(rffi.INT, category))

    return space.wrap(rffi.charp2str(result))

dcgettext.unwrap_spec = [ObjSpace, W_Root, str, int]


_textdomain = external('textdomain', [rffi.CCHARP], rffi.CCHARP)

def textdomain(space, w_domain):
    """textdomain(domain) -> string
    Set the C library's textdomain to domain, returning the new domain."""

    if space.is_w(w_domain, space.w_None):
        domain = None
        result = _textdomain(domain)
    else:
        domain = space.str_w(w_domain)
        result = _textdomain(rffi.str2charp(domain))

    return space.wrap(rffi.charp2str(result))

textdomain.unwrap_spec = [ObjSpace, W_Root]

nl_item = rffi.INT
_nl_langinfo = external('nl_langinfo', [nl_item], rffi.CCHARP)

def nl_langinfo(space, key):
    """nl_langinfo(key) -> string
    Return the value for the locale information associated with key."""

    if key in constants.values():
        result = _nl_langinfo(rffi.cast(nl_item, key))
        return space.wrap(rffi.charp2str(result))
    raise OperationError(space.w_ValueError, "unsupported langinfo constant")

nl_langinfo.unwrap_spec = [ObjSpace, int]

_bindtextdomain = external('bindtextdomain', [rffi.CCHARP, rffi.CCHARP],
                                                                rffi.CCHARP)

def bindtextdomain(space, domain, w_dir):
    """bindtextdomain(domain, dir) -> string
    Bind the C library's domain to dir."""

    if space.is_w(w_dir, space.w_None):
        dir = None
        dirname = _bindtextdomain(rffi.str2charp(domain), dir)
    else:
        dir = space.str_w(w_dir)
        dirname = _bindtextdomain(rffi.str2charp(domain), rffi.str2charp(dir))

    if not dirname:
        errno = rposix.get_errno()
        raise OperationError(space.w_OSError, errno)
    return space.wrap(rffi.charp2str(dirname))

bindtextdomain.unwrap_spec = [ObjSpace, str, W_Root]

_bind_textdomain_codeset = external('bind_textdomain_codeset',
                                    [rffi.CCHARP, rffi.CCHARP], rffi.CCHARP)

# TODO: platform dependent
def bind_textdomain_codeset(space, domain, w_codeset):
    """bind_textdomain_codeset(domain, codeset) -> string
    Bind the C library's domain to codeset."""

    if space.is_w(w_codeset, space.w_None):
        codeset = None
        result = _bind_textdomain_codeset(rffi.str2charp(domain), codeset)
    else:
        codeset = space.str_w(w_codeset)
        result = _bind_textdomain_codeset(rffi.str2charp(domain),
                                        rffi.str2charp(codeset))
    
    if not result:
        return space.w_None
    else:
        return space.wrap(rffi.charp2str(result))

bind_textdomain_codeset.unwrap_spec = [ObjSpace, str, W_Root]
