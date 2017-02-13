"""
Provides internal 'locale' codecs (via POSIX wcstombs/mbrtowc) for use
by PyUnicode_Decode/EncodeFSDefault during interpreter bootstrap
"""
import os
import py
import sys
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rstring import UnicodeBuilder, assert_str0
from rpython.rlib.runicode import (code_to_unichr,
    default_unicode_error_decode, default_unicode_error_encode)
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo

from pypy.interpreter.error import strerror as _strerror

cwd = py.path.local(__file__).dirpath()
eci = ExternalCompilationInfo(
    includes=[cwd.join('locale_codec.h')],
    include_dirs=[str(cwd), cdir],
    separate_module_files=[cwd.join('locale_codec.c')])

def llexternal(*args, **kwargs):
    kwargs.setdefault('compilation_info', eci)
    kwargs.setdefault('sandboxsafe', True)
    kwargs.setdefault('_nowrapper', True)
    return rffi.llexternal(*args, **kwargs)

# An actual wchar_t*, rffi.CWCHARP is an array of UniChar (possibly on a
# narrow build)
RAW_WCHARP = lltype.Ptr(lltype.Array(rffi.WCHAR_T, hints={'nolength': True}))
pypy_char2wchar = llexternal('pypy_char2wchar', [rffi.CCHARP, rffi.SIZE_TP],
                             RAW_WCHARP)
pypy_char2wchar_free = llexternal('pypy_char2wchar_free', [RAW_WCHARP],
                                  lltype.Void)
pypy_wchar2char = llexternal('pypy_wchar2char', [RAW_WCHARP, rffi.SIZE_TP],
                             rffi.CCHARP)
pypy_wchar2char_free = llexternal('pypy_wchar2char_free', [rffi.CCHARP],
                                  lltype.Void)


def unicode_encode_locale_surrogateescape(u, errorhandler=None):
    """Encode unicode via the locale codecs (POSIX wcstombs) with the
    surrogateescape handler.

    The optional errorhandler is only called in the case of fatal
    errors.
    """
    if errorhandler is None:
        errorhandler = default_unicode_error_encode

    with lltype.scoped_alloc(rffi.SIZE_TP.TO, 1) as errorposp:
        with scoped_unicode2rawwcharp(u) as ubuf:
            sbuf = pypy_wchar2char(ubuf, errorposp)
        try:
            if not sbuf:
                errorpos = rffi.cast(lltype.Signed, errorposp[0])
                if errorpos == -1:
                    raise MemoryError
                errmsg = _errmsg(u"pypy_wchar2char")
                errorhandler('strict', 'filesystemencoding', errmsg, u,
                             errorpos, errorpos + 1)
            return rffi.charp2str(sbuf)
        finally:
            pypy_wchar2char_free(sbuf)


def str_decode_locale_surrogateescape(s, errorhandler=None):
    """Decode strs via the locale codecs (POSIX mrbtowc) with the
    surrogateescape handler.

    The optional errorhandler is only called in the case of fatal
    errors.
    """
    if errorhandler is None:
        errorhandler = default_unicode_error_decode

    with lltype.scoped_alloc(rffi.SIZE_TP.TO, 1) as sizep:
        with rffi.scoped_str2charp(s) as sbuf:
            ubuf = pypy_char2wchar(sbuf, sizep)
        try:
            if not ubuf:
                errmsg = _errmsg(u"pypy_char2wchar")
                errorhandler('strict', 'filesystemencoding', errmsg, s, 0, 1)
            size = rffi.cast(lltype.Signed, sizep[0])
            return rawwcharp2unicoden(ubuf, size)
        finally:
            pypy_char2wchar_free(ubuf)


def _errmsg(what):
    # I *think* that the functions in locale_codec.c don't set errno
    return u"%s failed" % what


class scoped_unicode2rawwcharp:
    def __init__(self, value):
        if value is not None:
            self.buf = unicode2rawwcharp(value)
        else:
            self.buf = lltype.nullptr(RAW_WCHARP.TO)
    def __enter__(self):
        return self.buf
    def __exit__(self, *args):
        if self.buf:
            lltype.free(self.buf, flavor='raw')

def unicode2rawwcharp(u):
    """unicode -> raw wchar_t*"""
    if _should_merge_surrogates():
        size = _unicode2rawwcharp_loop(u, lltype.nullptr(RAW_WCHARP.TO))
    else:
        size = len(u)
    array = lltype.malloc(RAW_WCHARP.TO, size + 1, flavor='raw')
    array[size] = rffi.cast(rffi.WCHAR_T, u'\x00')
    _unicode2rawwcharp_loop(u, array)
    return array
unicode2rawwcharp._annenforceargs_ = [unicode]

def _unicode2rawwcharp_loop(u, array):
    ulen = len(u)
    count = i = 0
    while i < ulen:
        oc = ord(u[i])
        if (_should_merge_surrogates() and
            0xD800 <= oc <= 0xDBFF and i + 1 < ulen and
            0xDC00 <= ord(u[i + 1]) <= 0xDFFF):
            if array:
                merged = (((oc & 0x03FF) << 10) |
                          (ord(u[i + 1]) & 0x03FF)) + 0x10000
                array[count] = rffi.cast(rffi.WCHAR_T, merged)
            i += 2
        else:
            if array:
                array[count] = rffi.cast(rffi.WCHAR_T, oc)
            i += 1
        count += 1
    return count
_unicode2rawwcharp_loop._annenforceargs_ = [unicode, None]


def rawwcharp2unicoden(wcp, maxlen):
    b = UnicodeBuilder(maxlen)
    i = 0
    while i < maxlen and rffi.cast(lltype.Signed, wcp[i]) != 0:
        b.append(code_to_unichr(wcp[i]))
        i += 1
    return assert_str0(b.build())
rawwcharp2unicoden._annenforceargs_ = [None, int]


def _should_merge_surrogates():
    if we_are_translated():
        unichar_size = rffi.sizeof(lltype.UniChar)
    else:
        unichar_size = 2 if sys.maxunicode == 0xFFFF else 4
    return unichar_size == 2 and rffi.sizeof(rffi.WCHAR_T) == 4
