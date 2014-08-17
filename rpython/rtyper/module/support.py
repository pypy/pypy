import sys

from rpython.annotator import model as annmodel
from rpython.rtyper.lltypesystem import lltype, rffi

_WIN32 = sys.platform.startswith('win')
UNDERSCORE_ON_WIN32 = '_' if _WIN32 else ''

# utility conversion functions
class LLSupport:
    _mixin_ = True

    def to_rstr(s):
        from rpython.rtyper.lltypesystem.rstr import STR, mallocstr
        if s is None:
            return lltype.nullptr(STR)
        p = mallocstr(len(s))
        for i in range(len(s)):
            p.chars[i] = s[i]
        return p
    to_rstr = staticmethod(to_rstr)

    def to_runicode(s):
        from rpython.rtyper.lltypesystem.rstr import UNICODE, mallocunicode
        if s is None:
            return lltype.nullptr(UNICODE)
        p = mallocunicode(len(s))
        for i in range(len(s)):
            p.chars[i] = s[i]
        return p
    to_runicode = staticmethod(to_runicode)

    def from_rstr(rs):
        if not rs:   # null pointer
            return None
        else:
            return ''.join([rs.chars[i] for i in range(len(rs.chars))])
    from_rstr = staticmethod(from_rstr)

    def from_rstr_nonnull(rs):
        assert rs
        return ''.join([rs.chars[i] for i in range(len(rs.chars))])
    from_rstr_nonnull = staticmethod(from_rstr_nonnull)


class StringTraits:
    str = str
    str0 = annmodel.s_Str0
    CHAR = rffi.CHAR
    CCHARP = rffi.CCHARP
    charp2str = staticmethod(rffi.charp2str)
    scoped_str2charp = staticmethod(rffi.scoped_str2charp)
    str2charp = staticmethod(rffi.str2charp)
    free_charp = staticmethod(rffi.free_charp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_buffer)

    @staticmethod
    def posix_function_name(name):
        return UNDERSCORE_ON_WIN32 + name

    @staticmethod
    def ll_os_name(name):
        return 'll_os.ll_os_' + name

class UnicodeTraits:
    str = unicode
    str0 = annmodel.s_Unicode0
    CHAR = rffi.WCHAR_T
    CCHARP = rffi.CWCHARP
    charp2str = staticmethod(rffi.wcharp2unicode)
    str2charp = staticmethod(rffi.unicode2wcharp)
    scoped_str2charp = staticmethod(rffi.scoped_unicode2wcharp)
    free_charp = staticmethod(rffi.free_wcharp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_unicodebuffer)

    @staticmethod
    def posix_function_name(name):
        return UNDERSCORE_ON_WIN32 + 'w' + name

    @staticmethod
    def ll_os_name(name):
        return 'll_os.ll_os_w' + name


def ll_strcpy(dst_s, src_s, n):
    dstchars = dst_s.chars
    srcchars = src_s.chars
    i = 0
    while i < n:
        dstchars[i] = srcchars[i]
        i += 1

def _ll_strfill(dst_s, srcchars, n):
    dstchars = dst_s.chars
    i = 0
    while i < n:
        dstchars[i] = srcchars[i]
        i += 1
