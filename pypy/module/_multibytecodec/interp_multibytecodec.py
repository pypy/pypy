from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ObjSpace, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import OperationError
from pypy.module._multibytecodec import c_codecs


class MultibyteCodec(Wrappable):

    def __init__(self, name, codec):
        self.name = name
        self.codec = codec

    @unwrap_spec(input=str, errors="str_or_None")
    def decode(self, space, input, errors=None):
        if errors is None:
            errors = 'strict'
        #
        try:
            output = c_codecs.decode(self.codec, input, errors)
        except c_codecs.EncodeDecodeError, e:
            raise OperationError(
                space.w_UnicodeDecodeError,
                space.newtuple([
                    space.wrap(self.name),
                    space.wrap(input),
                    space.wrap(e.start),
                    space.wrap(e.end),
                    space.wrap(e.reason)]))
        except RuntimeError:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("internal codec error"))
        return space.newtuple([space.wrap(output),
                               space.wrap(len(input))])

    @unwrap_spec(input=unicode, errors="str_or_None")
    def encode(self, space, input, errors=None):
        if errors is None:
            errors = 'strict'
        #
        try:
            output = c_codecs.encode(self.codec, input, errors)
        except c_codecs.EncodeDecodeError, e:
            raise OperationError(
                space.w_UnicodeEncodeError,
                space.newtuple([
                    space.wrap(self.name),
                    space.wrap(input),
                    space.wrap(e.start),
                    space.wrap(e.end),
                    space.wrap(e.reason)]))
        except RuntimeError:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("internal codec error"))
        return space.newtuple([space.wrap(output),
                               space.wrap(len(input))])


MultibyteCodec.typedef = TypeDef(
    'MultibyteCodec',
    __module__ = '_multibytecodec',
    decode = interp2app(MultibyteCodec.decode),
    encode = interp2app(MultibyteCodec.encode),
    )
MultibyteCodec.typedef.acceptable_as_base_class = False


@unwrap_spec(name=str)
def getcodec(space, name):
    try:
        codec = c_codecs.getcodec(name)
    except KeyError:
        raise OperationError(space.w_LookupError,
                             space.wrap("no such codec is supported."))
    return space.wrap(MultibyteCodec(name, codec))
