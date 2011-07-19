from pypy.rlib import rposix
from pypy.rlib.rarithmetic import intmask

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec

from pypy.rlib import rlocale
from pypy.module.exceptions.interp_exceptions import _new_exception, W_Exception
from pypy.rpython.lltypesystem import lltype, rffi

W_Error = _new_exception('Error', W_Exception, 'locale error')

import sys

def make_error(space, msg):
    return OperationError(space.gettypeobject(W_Error.typedef), space.wrap(msg))

def rewrap_error(space, e):
    return OperationError(space.gettypeobject(W_Error.typedef),
                          space.wrap(e.message))

def _fixup_ulcase(space):
    stringmod = space.call_function(
        space.getattr(space.getbuiltinmodule('__builtin__'),
                      space.wrap('__import__')), space.wrap('string'))
    # create uppercase map string
    ul = []
    for c in xrange(256):
        if rlocale.isupper(c):
            ul.append(chr(c))
    space.setattr(stringmod, space.wrap('uppercase'), space.wrap(''.join(ul)))

    # create lowercase string
    ul = []
    for c in xrange(256):
        if rlocale.islower(c):
            ul.append(chr(c))
    space.setattr(stringmod, space.wrap('lowercase'), space.wrap(''.join(ul)))

    # create letters string
    ul = []
    for c in xrange(256):
        if rlocale.isalpha(c):
            ul.append(chr(c))
    space.setattr(stringmod, space.wrap('letters'), space.wrap(''.join(ul)))

@unwrap_spec(category=int)
def setlocale(space, category, w_locale=None):
    "(integer,string=None) -> string. Activates/queries locale processing."

    if space.is_w(w_locale, space.w_None) or w_locale is None:
        locale = None
    else:
        locale = space.str_w(w_locale)
    try:
        result = rlocale.setlocale(category, locale)
    except rlocale.LocaleError, e:
        raise rewrap_error(space, e)

    # record changes to LC_CTYPE
    if category in (rlocale.LC_CTYPE, rlocale.LC_ALL):
        _fixup_ulcase(space)

    return space.wrap(result)

def _w_copy_grouping(space, text):
    groups = [ space.wrap(ord(group)) for group in text ]
    if groups:
        groups.append(space.wrap(0))
    return space.newlist(groups)

def localeconv(space):
    "() -> dict. Returns numeric and monetary locale-specific parameters."
    lp = rlocale.localeconv()

    # Numeric information
    w_result = space.newdict()
    w = space.wrap
    space.setitem(w_result, w("decimal_point"),
                  w(rffi.charp2str(lp.c_decimal_point)))
    space.setitem(w_result, w("thousands_sep"),
                  w(rffi.charp2str(lp.c_thousands_sep)))
    space.setitem(w_result, w("grouping"),
                  _w_copy_grouping(space, rffi.charp2str(lp.c_grouping)))
    space.setitem(w_result, w("int_curr_symbol"),
                  w(rffi.charp2str(lp.c_int_curr_symbol)))
    space.setitem(w_result, w("currency_symbol"),
                  w(rffi.charp2str(lp.c_currency_symbol)))
    space.setitem(w_result, w("mon_decimal_point"),
                  w(rffi.charp2str(lp.c_mon_decimal_point)))
    space.setitem(w_result, w("mon_thousands_sep"),
                  w(rffi.charp2str(lp.c_mon_thousands_sep)))
    space.setitem(w_result, w("mon_grouping"),
                  _w_copy_grouping(space, rffi.charp2str(lp.c_mon_grouping)))
    space.setitem(w_result, w("positive_sign"),
                  w(rffi.charp2str(lp.c_positive_sign)))
    space.setitem(w_result, w("negative_sign"),
                  w(rffi.charp2str(lp.c_negative_sign)))
    space.setitem(w_result, w("int_frac_digits"),
                  w(lp.c_int_frac_digits))
    space.setitem(w_result, w("frac_digits"),
                  w(lp.c_frac_digits))
    space.setitem(w_result, w("p_cs_precedes"),
                  w(lp.c_p_cs_precedes))
    space.setitem(w_result, w("p_sep_by_space"),
                  w(lp.c_p_sep_by_space))
    space.setitem(w_result, w("n_cs_precedes"),
                  w(lp.c_n_cs_precedes))
    space.setitem(w_result, w("n_sep_by_space"),
                  w(lp.c_n_sep_by_space))
    space.setitem(w_result, w("p_sign_posn"),
                  w(lp.c_p_sign_posn))
    space.setitem(w_result, w("n_sign_posn"),
                  w(lp.c_n_sign_posn))

    return w_result

_strcoll = rlocale.external('strcoll', [rffi.CCHARP, rffi.CCHARP], rffi.INT)
_wcscoll = rlocale.external('wcscoll', [rffi.CWCHARP, rffi.CWCHARP], rffi.INT)

def strcoll(space, w_s1, w_s2):
    "string,string -> int. Compares two strings according to the locale."

    if space.is_true(space.isinstance(w_s1, space.w_str)) and \
       space.is_true(space.isinstance(w_s2, space.w_str)):

        s1, s2 = space.str_w(w_s1), space.str_w(w_s2)
        s1_c = rffi.str2charp(s1)
        s2_c = rffi.str2charp(s2)
        try:
            return space.wrap(_strcoll(s1_c, s2_c))
        finally:
            rffi.free_charp(s1_c)
            rffi.free_charp(s2_c)

    #if not space.is_true(space.isinstance(w_s1, space.w_unicode)) and \
    #   not space.is_true(space.isinstance(w_s2, space.w_unicode)):
    #    raise OperationError(space.w_ValueError,
    #                         space.wrap("strcoll arguments must be strings"))

    s1, s2 = space.unicode_w(w_s1), space.unicode_w(w_s2)

    s1_c = rffi.unicode2wcharp(s1)
    s2_c = rffi.unicode2wcharp(s2)
    try:
        result = _wcscoll(s1_c, s2_c)
    finally:
        rffi.free_wcharp(s1_c)
        rffi.free_wcharp(s2_c)

    return space.wrap(result)

_strxfrm = rlocale.external('strxfrm',
                    [rffi.CCHARP, rffi.CCHARP, rffi.SIZE_T], rffi.SIZE_T)

@unwrap_spec(s=str)
def strxfrm(space, s):
    "string -> string. Returns a string that behaves for cmp locale-aware."
    n1 = len(s) + 1

    buf = lltype.malloc(rffi.CCHARP.TO, n1, flavor="raw", zero=True)
    s_c = rffi.str2charp(s)
    try:
        n2 = _strxfrm(buf, s_c, n1) + 1
    finally:
        rffi.free_charp(s_c)
    if n2 > n1:
        # more space needed
        lltype.free(buf, flavor="raw")
        buf = lltype.malloc(rffi.CCHARP.TO, intmask(n2),
                            flavor="raw", zero=True)
        s_c = rffi.str2charp(s)
        try:
            _strxfrm(buf, s_c, n2)
        finally:
            rffi.free_charp(s_c)

    val = rffi.charp2str(buf)
    lltype.free(buf, flavor="raw")

    return space.wrap(val)

if rlocale.HAVE_LANGINFO:

    @unwrap_spec(key=int)
    def nl_langinfo(space, key):
        """nl_langinfo(key) -> string
        Return the value for the locale information associated with key."""

        try:
            return space.wrap(rlocale.nl_langinfo(key))
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("unsupported langinfo constant"))

#___________________________________________________________________
# HAVE_LIBINTL dependence

if rlocale.HAVE_LIBINTL:
    _gettext = rlocale.external('gettext', [rffi.CCHARP], rffi.CCHARP)

    @unwrap_spec(msg=str)
    def gettext(space, msg):
        """gettext(msg) -> string
        Return translation of msg."""
        msg_c = rffi.str2charp(msg)
        try:
            return space.wrap(rffi.charp2str(_gettext(msg_c)))
        finally:
            rffi.free_charp(msg_c)

    _dgettext = rlocale.external('dgettext', [rffi.CCHARP, rffi.CCHARP], rffi.CCHARP)

    @unwrap_spec(msg=str)
    def dgettext(space, w_domain, msg):
        """dgettext(domain, msg) -> string
        Return translation of msg in domain."""
        if space.is_w(w_domain, space.w_None):
            domain = None
            msg_c = rffi.str2charp(msg)
            try:
                result = _dgettext(domain, msg_c)
                # note that 'result' may be the same pointer as 'msg_c',
                # so it must be converted to an RPython string *before*
                # we free msg_c.
                result = rffi.charp2str(result)
            finally:
                rffi.free_charp(msg_c)
        else:
            domain = space.str_w(w_domain)
            domain_c = rffi.str2charp(domain)
            msg_c = rffi.str2charp(msg)
            try:
                result = _dgettext(domain_c, msg_c)
                # note that 'result' may be the same pointer as 'msg_c',
                # so it must be converted to an RPython string *before*
                # we free msg_c.
                result = rffi.charp2str(result)
            finally:
                rffi.free_charp(domain_c)
                rffi.free_charp(msg_c)

        return space.wrap(result)

    _dcgettext = rlocale.external('dcgettext', [rffi.CCHARP, rffi.CCHARP, rffi.INT],
                                                                rffi.CCHARP)

    @unwrap_spec(msg=str, category=int)
    def dcgettext(space, w_domain, msg, category):
        """dcgettext(domain, msg, category) -> string
        Return translation of msg in domain and category."""

        if space.is_w(w_domain, space.w_None):
            domain = None
            msg_c = rffi.str2charp(msg)
            try:
                result = _dcgettext(domain, msg_c, rffi.cast(rffi.INT, category))
                # note that 'result' may be the same pointer as 'msg_c',
                # so it must be converted to an RPython string *before*
                # we free msg_c.
                result = rffi.charp2str(result)
            finally:
                rffi.free_charp(msg_c)
        else:
            domain = space.str_w(w_domain)
            domain_c = rffi.str2charp(domain)
            msg_c = rffi.str2charp(msg)
            try:
                result = _dcgettext(domain_c, msg_c,
                                    rffi.cast(rffi.INT, category))
                # note that 'result' may be the same pointer as 'msg_c',
                # so it must be converted to an RPython string *before*
                # we free msg_c.
                result = rffi.charp2str(result)
            finally:
                rffi.free_charp(domain_c)
                rffi.free_charp(msg_c)

        return space.wrap(result)


    _textdomain = rlocale.external('textdomain', [rffi.CCHARP], rffi.CCHARP)

    def textdomain(space, w_domain):
        """textdomain(domain) -> string
        Set the C library's textdomain to domain, returning the new domain."""

        if space.is_w(w_domain, space.w_None):
            domain = None
            result = _textdomain(domain)
            result = rffi.charp2str(result)
        else:
            domain = space.str_w(w_domain)
            domain_c = rffi.str2charp(domain)
            try:
                result = _textdomain(domain_c)
                # note that 'result' may be the same pointer as 'domain_c'
                # (maybe?) so it must be converted to an RPython string
                # *before* we free domain_c.
                result = rffi.charp2str(result)
            finally:
                rffi.free_charp(domain_c)

        return space.wrap(result)

    _bindtextdomain = rlocale.external('bindtextdomain', [rffi.CCHARP, rffi.CCHARP],
                                                                rffi.CCHARP)

    @unwrap_spec(domain=str)
    def bindtextdomain(space, domain, w_dir):
        """bindtextdomain(domain, dir) -> string
        Bind the C library's domain to dir."""

        if space.is_w(w_dir, space.w_None):
            dir = None
            domain_c = rffi.str2charp(domain)
            try:
                dirname = _bindtextdomain(domain_c, dir)
            finally:
                rffi.free_charp(domain_c)
        else:
            dir = space.str_w(w_dir)
            domain_c = rffi.str2charp(domain)
            dir_c = rffi.str2charp(dir)
            try:
                dirname = _bindtextdomain(domain_c, dir_c)
            finally:
                rffi.free_charp(domain_c)
                rffi.free_charp(dir_c)

        if not dirname:
            errno = rposix.get_errno()
            raise OperationError(space.w_OSError, space.wrap(errno))
        return space.wrap(rffi.charp2str(dirname))

    _bind_textdomain_codeset = rlocale.external('bind_textdomain_codeset',
                                    [rffi.CCHARP, rffi.CCHARP], rffi.CCHARP)

    if rlocale.HAVE_BIND_TEXTDOMAIN_CODESET:
        @unwrap_spec(domain=str)
        def bind_textdomain_codeset(space, domain, w_codeset):
            """bind_textdomain_codeset(domain, codeset) -> string
            Bind the C library's domain to codeset."""

            if space.is_w(w_codeset, space.w_None):
                codeset = None
                domain_c = rffi.str2charp(domain)
                try:
                    result = _bind_textdomain_codeset(domain_c, codeset)
                finally:
                    rffi.free_charp(domain_c)
            else:
                codeset = space.str_w(w_codeset)
                domain_c = rffi.str2charp(domain)
                codeset_c = rffi.str2charp(codeset)
                try:
                    result = _bind_textdomain_codeset(domain_c, codeset_c)
                finally:
                    rffi.free_charp(domain_c)
                    rffi.free_charp(codeset_c)

            if not result:
                return space.w_None
            else:
                return space.wrap(rffi.charp2str(result))

if sys.platform == 'win32':
    def getdefaultlocale(space):
        language, encoding = rlocale.getdefaultlocale()
        return space.newtuple([space.wrap(language), space.wrap(encoding)])
