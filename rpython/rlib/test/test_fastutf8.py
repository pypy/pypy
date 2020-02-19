#encoding: utf-8
import pytest
import sys
from hypothesis import given, strategies as st, settings, example

from rpython.rlib.fastutf8 import fu8
from rpython.rtyper.lltypesystem import lltype, rffi

def _check_size(bytes, size):
    ptr = rffi.str2charp(bytes)
    assert fu8.count_utf8_codepoints(ptr, len(bytes)) == size
    rffi.free_charp(ptr)

@given(st.text(alphabet=st.characters(whitelist_categories=('Lu','Lo','So')), min_size=15))
def test_unichr_as_utf8(chars):
    print(chars)
    _check_size(chars.encode('utf-8'), len(chars))
    chars_double = chars+chars
    _check_size(chars_double.encode('utf-8'), len(chars_double))

def test_avx_crash():
    text = u'AAAAAAAAAAAAA\xa6\xa6AAAAAAAAAAAAAAAAA'
    _check_size(text.encode('utf-8'), len(text))
