# encoding: iso-8859-15
from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi, lltype

class TestCodecs(BaseApiTest):
    def test_incremental(self, space, api):
        utf8 = rffi.str2charp('utf-8')
        w_encoder = api.PyCodec_IncrementalEncoder(utf8, None)
        w_encoded = space.call_method(w_encoder, 'encode', space.wrap(u'späm'))
        w_decoder = api.PyCodec_IncrementalDecoder(utf8, None)
        w_decoded = space.call_method(w_decoder, 'decode', w_encoded)
        assert space.unwrap(w_decoded) == u'späm'
        rffi.free_charp(utf8)

