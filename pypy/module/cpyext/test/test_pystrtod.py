import math

from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype


class TestPyOS_string_to_double(BaseApiTest):

    def test_simple_float(self, api):
        s = rffi.str2charp('0.4')
        null = lltype.nullptr(rffi.CCHARPP.TO)
        r = api.PyOS_string_to_double(s, null, None)
        assert r == 0.4
        rffi.free_charp(s)

    def test_empty_string(self, api):
        s = rffi.str2charp('')
        null = lltype.nullptr(rffi.CCHARPP.TO)
        r = api.PyOS_string_to_double(s, null, None)
        assert r == -1.0
        raises(ValueError)
        api.PyErr_Clear()
        rffi.free_charp(s)

    def test_bad_string(self, api):
        s = rffi.str2charp(' 0.4')
        null = lltype.nullptr(rffi.CCHARPP.TO)
        r = api.PyOS_string_to_double(s, null, None)
        assert r == -1.0
        raises(ValueError)
        api.PyErr_Clear()
        rffi.free_charp(s)

    def test_overflow_pos(self, api):
        s = rffi.str2charp('1e500')
        null = lltype.nullptr(rffi.CCHARPP.TO)
        r = api.PyOS_string_to_double(s, null, None)
        assert math.isinf(r)
        assert r > 0
        rffi.free_charp(s)

    def test_overflow_neg(self, api):
        s = rffi.str2charp('-1e500')
        null = lltype.nullptr(rffi.CCHARPP.TO)
        r = api.PyOS_string_to_double(s, null, None)
        assert math.isinf(r)
        assert r < 0
        rffi.free_charp(s)

    def test_overflow_exc(self, space, api):
        s = rffi.str2charp('1e500')
        null = lltype.nullptr(rffi.CCHARPP.TO)
        r = api.PyOS_string_to_double(s, null, space.w_ValueError)
        assert r == -1.0
        raises(ValueError)
        api.PyErr_Clear()
        rffi.free_charp(s)

    def test_endptr_number(self, api):
        s = rffi.str2charp('0.4')
        endp = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        r = api.PyOS_string_to_double(s, endp, None)
        assert r == 0.4
        endp_addr = rffi.cast(rffi.LONG, endp[0])
        s_addr = rffi.cast(rffi.LONG, s)
        assert endp_addr == s_addr + 3
        rffi.free_charp(s)
        lltype.free(endp, flavor='raw')

    def test_endptr_tail(self, api):
        s = rffi.str2charp('0.4 foo')
        endp = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        r = api.PyOS_string_to_double(s, endp, None)
        assert r == 0.4
        endp_addr = rffi.cast(rffi.LONG, endp[0])
        s_addr = rffi.cast(rffi.LONG, s)
        assert endp_addr == s_addr + 3
        rffi.free_charp(s)
        lltype.free(endp, flavor='raw')

    def test_endptr_no_conversion(self, api):
        s = rffi.str2charp('foo')
        endp = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        r = api.PyOS_string_to_double(s, endp, None)
        assert r == -1.0
        raises(ValueError)
        endp_addr = rffi.cast(rffi.LONG, endp[0])
        s_addr = rffi.cast(rffi.LONG, s)
        assert endp_addr == s_addr
        api.PyErr_Clear()
        rffi.free_charp(s)
        lltype.free(endp, flavor='raw')
