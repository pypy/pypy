from pypy.module._io.interp_bufferedio import W_BufferedIOBase
from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr)

class W_BytesIO(W_BufferedIOBase):
    pass
W_BytesIO.typedef = TypeDef(
    'BytesIO', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BytesIO),
    )

