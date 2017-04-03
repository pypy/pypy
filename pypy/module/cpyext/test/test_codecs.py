# encoding: iso-8859-15
from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.codecs import (
    PyCodec_IncrementalEncoder, PyCodec_IncrementalDecoder)

class TestCodecs(BaseApiTest):
    def test_incremental(self, space):
        utf8 = rffi.str2charp('utf-8')
        w_encoder = PyCodec_IncrementalEncoder(space, utf8, None)
        w_encoded = space.call_method(w_encoder, 'encode', space.wrap(u'späm'))
        w_decoder = PyCodec_IncrementalDecoder(space, utf8, None)
        w_decoded = space.call_method(w_decoder, 'decode', w_encoded)
        assert space.unwrap(w_decoded) == u'späm'
        rffi.free_charp(utf8)
