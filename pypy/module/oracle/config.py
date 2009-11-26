from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.oracle import roci

WITH_UNICODE = False

MAX_STRING_CHARS = 4000
MAX_BINARY_BYTES = 4000

if WITH_UNICODE:
    CHARSETID = roci.OCI_UTF16ID
    BYTES_PER_CHAR = 2
    def string_w(space, w_obj):
        return space.unicode_w(w_obj)
else:
    def string_w(space, w_obj):
        return space.str_w(w_obj)

    def w_string(space, buf, len=-1):
        if len < 0:
            return space.wrap(rffi.charp2str(buf))
        else:
            return space.wrap(rffi.charpsize2str(buf, len))
    CHARSETID = 0
    BYTES_PER_CHAR = 1

    class StringBuffer:
        "Fill a char* buffer with data, suitable to pass to Oracle functions"
        def __init__(self):
            pass

        def fill(self, space, w_string):
            if w_string is None or space.is_w(w_string, space.w_None):
                self.clear()
            else:
                self.ptr = string_w(space, w_string)
                self.size = len(self.ptr)

        def fill_with_unicode(self, space, w_unicode):
            if w_unicode is None or space.is_w(w_unicode, space.w_None):
                self.clear()
            else:
                # XXX ucs2 only probably
                unistr = space.unicode_w(w_unicode)
                self.ptr = rffi.cast(roci.oratext, rffi.unicode2wcharp(unistr))
                self.size = len(unistr) * 2

        def clear(self):
            self.ptr = None
            self.size = 0
