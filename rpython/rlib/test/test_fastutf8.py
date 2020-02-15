#encoding: utf-8
import pytest
import sys
from hypothesis import given, strategies as st, settings, example

from rpython.rlib.fastutf8 import fu8
from rpython.rtyper.lltypesystem import lltype, rffi


@given(st.text(alphabet=st.characters(whitelist_categories=('Lu','Lo','So'))))
@example("\xf0\x90\x80\x80\xe0\xa0\x80\xe0\xa0\x80\xe0\xa0\x80\xf0\x90\x80\x80\xe0\xa0\x80\xf0\x90\x80\x80\xf0\x90\x80\x80\xf0\x90\x80\x80".decode('utf8'))
def test_unichr_as_utf8(chars):
    print(chars)
    bytes = chars.encode('utf-8')
    ptr = rffi.str2charp(bytes)
    assert fu8.count_utf8_codepoints(ptr, len(bytes)) == len(chars)
    rffi.free_charp(ptr)
