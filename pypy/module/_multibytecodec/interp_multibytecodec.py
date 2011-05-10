from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ObjSpace, interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import OperationError
from pypy.module._multibytecodec import c_codecs


class MultibyteCodec(Wrappable):

    def __init__(self, name, codec):
        self.name = name
        self.codec = codec

    def decode(self, space, input, errors=None):
        if errors is not None and errors != 'strict':
            raise OperationError(space.w_NotImplementedError,    # XXX
                                 space.wrap("errors='%s' in _multibytecodec"
                                            % errors))
        #
        try:
            output = c_codecs.decode(self.codec, input)
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
    decode.unwrap_spec = ['self', ObjSpace, str, 'str_or_None']

    def encode(self):
        xxx


MultibyteCodec.typedef = TypeDef(
    'MultibyteCodec',
    __module__ = '_multibytecodec',
    decode = interp2app(MultibyteCodec.decode),
    encode = interp2app(MultibyteCodec.encode),
    )
MultibyteCodec.typedef.acceptable_as_base_class = False


def getcodec(space, name):
    try:
        codec = c_codecs.getcodec(name)
    except KeyError:
        raise OperationError(space.w_LookupError,
                             space.wrap("no such codec is supported."))
    return space.wrap(MultibyteCodec(name, codec))
getcodec.unwrap_spec = [ObjSpace, str]
