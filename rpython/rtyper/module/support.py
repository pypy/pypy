import sys

from rpython.annotator import model as annmodel
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import specialize
from rpython.rlib import rstring

_WIN32 = sys.platform.startswith('win')
UNDERSCORE_ON_WIN32 = '_' if _WIN32 else ''


class StringTraits:
    str = str
    str0 = annmodel.s_Str0
    CHAR = rffi.CHAR
    CCHARP = rffi.CCHARP
    charp2str = staticmethod(rffi.charp2str)
    charpsize2str = staticmethod(rffi.charpsize2str)
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

class UnicodeTraits:
    str = unicode
    str0 = annmodel.s_Unicode0
    CHAR = rffi.WCHAR_T
    CCHARP = rffi.CWCHARP
    charp2str = staticmethod(rffi.wcharp2unicode)
    charpsize2str = staticmethod(rffi.wcharpsize2unicode)
    str2charp = staticmethod(rffi.unicode2wcharp)
    scoped_str2charp = staticmethod(rffi.scoped_unicode2wcharp)
    free_charp = staticmethod(rffi.free_wcharp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_unicodebuffer)

    @staticmethod
    def posix_function_name(name):
        return UNDERSCORE_ON_WIN32 + 'w' + name

    @staticmethod
    @specialize.argtype(0)
    def ll_os_name(name):
        return 'll_os.ll_os_w' + name

    @staticmethod
    @specialize.argtype(0)
    def as_str(path):
        assert path is not None
        if isinstance(path, unicode):
            return path
        else:
            return path.as_unicode()
    
    @staticmethod
    @specialize.argtype(0)
    def as_str0(path):
        res = UnicodeTraits.as_str(path)
        rstring.check_str0(res)
        return res

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
