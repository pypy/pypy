from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.api import cpython_api, PyObject, CONST_STRING
from pypy.module._codecs import interp_codecs

@cpython_api([CONST_STRING, CONST_STRING], PyObject)
def PyCodec_IncrementalEncoder(space, encoding, errors):
    w_codec = interp_codecs.lookup_codec(space, rffi.charp2str(encoding))
    if errors:
        w_errors = space.newtext(rffi.charp2str(errors))
        return space.call_method(w_codec, "incrementalencoder", w_errors)
    else:
        return space.call_method(w_codec, "incrementalencoder")

@cpython_api([CONST_STRING, CONST_STRING], PyObject)
def PyCodec_IncrementalDecoder(space, encoding, errors):
    w_codec = interp_codecs.lookup_codec(space, rffi.charp2str(encoding))
    if errors:
        w_errors = space.newtext(rffi.charp2str(errors))
        return space.call_method(w_codec, "incrementaldecoder", w_errors)
    else:
        return space.call_method(w_codec, "incrementaldecoder")

