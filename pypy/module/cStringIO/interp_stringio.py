from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.rlib.rStringIO import RStringIO


PIECES = 80
BIGPIECES = 32


class W_OutputType(Wrappable, RStringIO):
    def __init__(self, space):
        RStringIO.__init__(self)
        self.space = space
        self.softspace = 0    # part of the file object API

    def descr_close(self):
        self.close()
    descr_close.unwrap_spec = ['self']

    def check_closed(self):
        if self.is_closed():
            space = self.space
            raise OperationError(space.w_ValueError,
                                 space.wrap("I/O operation on closed file"))

    def descr_getvalue(self):
        self.check_closed()
        return self.space.wrap(self.getvalue())
    descr_getvalue.unwrap_spec = ['self']

    def descr_read(self, n=-1):
        self.check_closed()
        return self.space.wrap(self.read(n))
    descr_read.unwrap_spec = ['self', int]

    def descr_reset(self):
        self.check_closed()
        self.seek(0)
    descr_reset.unwrap_spec = ['self']

    def descr_seek(self, position, mode=0):
        self.check_closed()
        self.seek(position, mode)
    descr_seek.unwrap_spec = ['self', int, int]

    def descr_tell(self):
        self.check_closed()
        return self.space.wrap(self.tell())
    descr_tell.unwrap_spec = ['self']

    def descr_write(self, buffer):
        self.check_closed()
        self.write(buffer)
    descr_write.unwrap_spec = ['self', 'bufferstr']

# ____________________________________________________________

def descr_closed(space, self):
    return space.wrap(self.strings is None)

def descr_softspace(space, self):
    return space.wrap(self.softspace)

def descr_setsoftspace(space, self, w_newvalue):
    self.softspace = space.int_w(w_newvalue)

W_OutputType.typedef = TypeDef(
    "cStringIO.StringO",
    close        = interp2app(W_OutputType.descr_close),
    closed       = GetSetProperty(descr_closed, cls=W_OutputType),
    getvalue     = interp2app(W_OutputType.descr_getvalue),
    read         = interp2app(W_OutputType.descr_read),
    reset        = interp2app(W_OutputType.descr_reset),
    seek         = interp2app(W_OutputType.descr_seek),
    softspace    = GetSetProperty(descr_softspace,
                                  descr_setsoftspace,
                                  cls=W_OutputType),
    tell         = interp2app(W_OutputType.descr_tell),
    write        = interp2app(W_OutputType.descr_write),
    )

# ____________________________________________________________

def StringIO(space):
    return space.wrap(W_OutputType(space))
