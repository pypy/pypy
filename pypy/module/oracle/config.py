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
        #assert type(len) is int
        if len < 0:
            return space.wrap(rffi.charp2str(buf))
        else:
            return space.wrap(rffi.charpsize2str(buf, len))
    CHARSETID = 0
    BYTES_PER_CHAR = 1

    class StringBuffer:
        "Fill a char* buffer with data, suitable to pass to Oracle functions"
        def __init__(self):
            self.ptr = lltype.nullptr(roci.oratext.TO)
            self.size = 0

        def fill(self, space, w_value):
            if w_value is None or space.is_w(w_value, space.w_None):
                self.clear()
            else:
                strvalue = space.str_w(w_value)
                self.ptr = rffi.str2charp(strvalue)
                self.size = len(strvalue)

        def fill_with_unicode(self, space, w_value):
            if w_value is None or space.is_w(w_value, space.w_None):
                self.clear()
            else:
                # XXX ucs2 only probably
                univalue = space.unicode_w(w_value)
                self.ptr = rffi.cast(roci.oratext, rffi.unicode2wcharp(univalue))
                self.size = len(univalue) * 2

        def clear(self):
            if self.ptr:
                rffi.free_charp(self.ptr)
                self.ptr = lltype.nullptr(roci.oratext.TO)
            self.size = 0
