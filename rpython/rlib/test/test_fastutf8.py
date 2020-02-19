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

@given(st.text(alphabet=st.characters(whitelist_categories=('Lu','Lo','So')), min_size=15, max_size=31))
def test_unichr_as_utf8_sse4(chars):
    _check_size(chars.encode('utf-8'), len(chars))

SOME = ('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Mn', 'Mc', 'Me', 'Nd', 'Nl', 'No', 'So',)
@given(st.text(alphabet=st.characters(whitelist_categories=SOME), min_size=31))
def test_unichr_as_utf8_avx(chars):
    _check_size(chars.encode('utf-8'), len(chars))

def test_avx_crash():
    text = u'AAAAAAAAAAAAA\xa6\xa6AAAAAAAAAAAAAAAAA'
    _check_size(text.encode('utf-8'), len(text))
