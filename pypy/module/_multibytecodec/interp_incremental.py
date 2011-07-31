from pypy.rpython.lltypesystem import lltype
from pypy.module._multibytecodec import c_codecs
from pypy.module._multibytecodec.interp_multibytecodec import (
    MultibyteCodec, wrap_unicodedecodeerror, wrap_runtimeerror)
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module._codecs.interp_codecs import CodecState


class MultibyteIncrementalDecoder(Wrappable):

    def __init__(self, space, errors):
        if errors is None:
            errors = 'strict'
        self.space = space
        self.errors = errors
        w_codec = space.getattr(space.wrap(self), space.wrap("codec"))
        codec = space.interp_w(MultibyteCodec, w_codec)
        self.codec = codec.codec
        self.name = codec.name
        self._initialize()

    def _initialize(self):
        self.decodebuf = c_codecs.pypy_cjk_dec_new(self.codec)
        self.pending = ""

    def _free(self):
        self.pending = None
        if self.decodebuf:
            pypy_cjk_dec_free(self.decodebuf)
            self.decodebuf = lltype.nullptr(DECODEBUF_P.TO)

    def __del__(self):
        self._free()

    def reset_w(self):
        self._free()
        self._initialize()

    @unwrap_spec(object=str, final=bool)
    def decode_w(self, object, final=False):
        space = self.space
        state = space.fromcache(CodecState)
        if len(self.pending) > 0:
            object = self.pending + object
        try:
            output = c_codecs.decodeex(self.decodebuf, object, self.errors,
                                       state.decode_error_handler, self.name,
                                       get_ignore_error(final))
        except c_codecs.EncodeDecodeError, e:
            raise wrap_unicodedecodeerror(space, e, object, self.name)
        except RuntimeError:
            raise wrap_runtimeerror(space)
        pos = c_codecs.pypy_cjk_dec_inbuf_consumed(self.decodebuf)
        assert 0 <= pos <= len(object)
        self.pending = object[pos:]
        return space.wrap(output)


@unwrap_spec(errors="str_or_None")
def mbidecoder_new(space, w_subtype, errors=None):
    r = space.allocate_instance(MultibyteIncrementalDecoder, w_subtype)
    r.__init__(space, errors)
    return space.wrap(r)

MultibyteIncrementalDecoder.typedef = TypeDef(
    'MultibyteIncrementalDecoder',
    __module__ = '_multibytecodec',
    __new__ = interp2app(mbidecoder_new),
    decode  = interp2app(MultibyteIncrementalDecoder.decode_w),
    reset   = interp2app(MultibyteIncrementalDecoder.reset_w),
    )


def get_ignore_error(final):
    if final:
        return 0    # don't ignore any error
    else:
        return c_codecs.MBERR_TOOFEW
