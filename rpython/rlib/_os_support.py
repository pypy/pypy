import sys

from rpython.annotator.model import s_Str0, s_Unicode0
from rpython.rlib import rstring
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import rffi


_CYGWIN = sys.platform == 'cygwin'
_WIN32 = sys.platform.startswith('win')
_LINUX = sys.platform.startswith('linux')
UNDERSCORE_ON_WIN32 = '_' if _WIN32 else ''
POSIX_SIZE_T = rffi.UINT if _WIN32 else rffi.SIZE_T
POSIX_SSIZE_T = rffi.INT if _WIN32 else rffi.SSIZE_T
_MACRO_ON_POSIX = True if not _WIN32 else None


class StringTraits(object):
    nickname = "bytes"
    str0 = s_Str0
    CHAR = rffi.CHAR
    CCHARP = rffi.CCHARP
    charp2str = staticmethod(rffi.charp2str)
    charpsize2str = staticmethod(rffi.charpsize2str)
    scoped_str2charp = staticmethod(rffi.scoped_str2charp)
    str2charp = staticmethod(rffi.str2charp)
    free_charp = staticmethod(rffi.free_charp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_buffer)

    @staticmethod
    @specialize.argtype(0)
    def as_str(path):
        assert path is not None
        if isinstance(path, str):
            return path
        elif isinstance(path, unicode):
            # This never happens in PyPy's Python interpreter!
            # Only in raw RPython code that uses unicode strings.
            # We implement python2 behavior: silently convert to ascii.
            return path.encode('ascii')
        else:
            return path.as_bytes()

    @staticmethod
    @specialize.argtype(0)
    def as_str0(path):
        res = StringTraits.as_str(path)
        rstring.check_str0(res)
        return res


class UnicodeTraits(object):
    nickname = "unicode"
    str0 = s_Unicode0
    CHAR = rffi.WCHAR_T
    CCHARP = rffi.CWCHARP
    charp2str = staticmethod(rffi.wcharp2unicode)
    charpsize2str = staticmethod(rffi.wcharpsize2unicode)
    str2charp = staticmethod(rffi.unicode2wcharp)
    scoped_str2charp = staticmethod(rffi.scoped_unicode2wcharp)
    free_charp = staticmethod(rffi.free_wcharp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_unicodebuffer)

    @staticmethod
    @specialize.argtype(0)
    def as_str(path):
        assert path is not None
        if isinstance(path, unicode):
            return path
        elif isinstance(path, str):
            raise RuntimeError('str given where unicode expected')
        else:
            return path.as_unicode()

    @staticmethod
    @specialize.argtype(0)
    def as_str0(path):
        res = UnicodeTraits.as_str(path)
        rstring.check_str0(res)
        return res


class Utf8Traits(object):
    nickname = "utf8"
    str = str
    str0 = s_Unicode0
    CHAR = rffi.WCHAR_T
    CCHARP = rffi.CWCHARP
    charp2str = staticmethod(rffi.wcharp2utf8)
    charpsize2str = staticmethod(rffi.wcharpsize2utf8)
    str2charp = staticmethod(rffi.utf82wcharp)
    scoped_str2charp = staticmethod(rffi.scoped_utf82wcharp)
    free_charp = staticmethod(rffi.free_wcharp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_unicodebuffer)

    @staticmethod
    @specialize.argtype(0)
    def as_str(path):
        assert path is not None
        if isinstance(path, str):
            return path
        elif isinstance(path, unicode):
            # This never happens in PyPy's Python interpreter!
            # Only in raw RPython code that uses unicode strings.
            # We implement python3 behavior: silently convert to utf8.
            return path.encode('utf8')
        else:
            return path.as_bytes()

    @staticmethod
    @specialize.argtype(0)
    def as_str0(path):
        res = Utf8Traits.as_str(path)
        rstring.check_str0(res)
        return res

    @staticmethod
    @specialize.argtype(0)
    def as_utf80(path):
        if isinstance(path, str):
            res = path
        elif isinstance(path, unicode):
            res = path.encode('utf-8')
        else:
            res = path.as_bytes()
        assert res is not None
        rstring.check_str0(res)
        return res


string_traits = StringTraits()
unicode_traits = UnicodeTraits()
utf8_traits = Utf8Traits()

# Always use utf8_traits
