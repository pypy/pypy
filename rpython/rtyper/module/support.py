import sys

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import specialize
from rpython.rlib import rstring

_WIN32 = sys.platform.startswith('win')
UNDERSCORE_ON_WIN32 = '_' if _WIN32 else ''

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
