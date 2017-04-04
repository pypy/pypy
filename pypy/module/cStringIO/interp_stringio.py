from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from rpython.rlib.rStringIO import RStringIO
from rpython.rlib.objectmodel import import_from_mixin


class W_InputOutputType(W_Root):
    softspace = 0    # part of the file object API

    def descr___iter__(self):
        self.check_closed()
        return self

    def descr_close(self):
        self.close()

    def check_closed(self):
        if self.is_closed():
            space = self.space
            raise oefmt(space.w_ValueError, "I/O operation on closed file")

    def descr_flush(self):
        self.check_closed()

    def descr_getvalue(self):
        self.check_closed()
        return self.space.newtext(self.getvalue())

    def descr_isatty(self):
        self.check_closed()
        return self.space.w_False

    def descr_next(self):
        space = self.space
        self.check_closed()
        line = self.readline()
        if len(line) == 0:
            raise OperationError(space.w_StopIteration, space.w_None)
        return space.newtext(line)

    @unwrap_spec(n=int)
    def descr_read(self, n=-1):
        self.check_closed()
        return self.space.newtext(self.read(n))

    @unwrap_spec(size=int)
    def descr_readline(self, size=-1):
        self.check_closed()
        return self.space.newtext(self.readline(size))

    @unwrap_spec(size=int)
    def descr_readlines(self, size=0):
        self.check_closed()
        lines_w = []
        while True:
            line = self.readline()
            if len(line) == 0:
                break
            lines_w.append(self.space.newtext(line))
            if size > 0:
                size -= len(line)
                if size <= 0:
                    break
        return self.space.newlist(lines_w)

    def descr_reset(self):
        self.check_closed()
        self.seek(0)

    @unwrap_spec(position=int, mode=int)
    def descr_seek(self, position, mode=0):
        self.check_closed()
        self.seek(position, mode)

    def descr_tell(self):
        self.check_closed()
        return self.space.newint(self.tell())

    # abstract methods
    def close(self):                  assert False, "abstract"
    def is_closed(self):              assert False, "abstract"
    def getvalue(self):               assert False, "abstract"
    def read(self, n=-1):             assert False, "abstract"
    def readline(self, size=-1):      assert False, "abstract"
    def seek(self, position, mode=0): assert False, "abstract"
    def tell(self):                   assert False, "abstract"

# ____________________________________________________________

class W_InputType(W_InputOutputType):
    def __init__(self, space, string):
        self.space = space
        self.string = string
        self.pos = 0

    def close(self):
        self.string = None

    def is_closed(self):
        return self.string is None

    def getvalue(self):
        return self.string

    def read(self, n=-1):
        p = self.pos
        count = len(self.string) - p
        if n >= 0:
            count = min(n, count)
        if count <= 0:
            return ''
        self.pos = p + count
        if count == len(self.string):
            return self.string
        else:
            return self.string[p:p+count]

    def readline(self, size=-1):
        p = self.pos
        end = len(self.string)
        if size >= 0 and size < end - p:
            end = p + size
        lastp = self.string.find('\n', p, end)
        if lastp < 0:
            endp = end
        else:
            endp = lastp + 1
        self.pos = endp
        return self.string[p:endp]

    def seek(self, position, mode=0):
        if mode == 1:
            position += self.pos
        elif mode == 2:
            position += len(self.string)
        if position < 0:
            position = 0
        self.pos = position

    def tell(self):
        return self.pos

# ____________________________________________________________

class W_OutputType(W_InputOutputType):
    import_from_mixin(RStringIO)

    def __init__(self, space):
        self.init()
        self.space = space

    def descr_truncate(self, w_size=None):
        self.check_closed()
        space = self.space
        if space.is_none(w_size):
            size = self.tell()
        else:
            size = space.int_w(w_size)
        if size < 0:
            raise oefmt(space.w_IOError, "negative size")
        self.truncate(size)

    def descr_write(self, space, w_buffer):
        buffer = space.getarg_w('s*', w_buffer)
        self.check_closed()
        self.write(buffer.as_str())

    def descr_writelines(self, w_lines):
        self.check_closed()
        space = self.space
        w_iterator = space.iter(w_lines)
        while True:
            try:
                w_line = space.next(w_iterator)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break  # done
            self.write(space.text_w(w_line))

# ____________________________________________________________

def descr_closed(self, space):
    return space.newbool(self.is_closed())

def descr_softspace(self, space):
    return space.newint(self.softspace)

def descr_setsoftspace(self, space, w_newvalue):
    self.softspace = space.int_w(w_newvalue)

common_descrs = {
    '__iter__':     interp2app(W_InputOutputType.descr___iter__),
    'close':        interp2app(W_InputOutputType.descr_close),
    'flush':        interp2app(W_InputOutputType.descr_flush),
    'getvalue':     interp2app(W_InputOutputType.descr_getvalue),
    'isatty':       interp2app(W_InputOutputType.descr_isatty),
    'next':         interp2app(W_InputOutputType.descr_next),
    'read':         interp2app(W_InputOutputType.descr_read),
    'readline':     interp2app(W_InputOutputType.descr_readline),
    'readlines':    interp2app(W_InputOutputType.descr_readlines),
    'reset':        interp2app(W_InputOutputType.descr_reset),
    'seek':         interp2app(W_InputOutputType.descr_seek),
    'tell':         interp2app(W_InputOutputType.descr_tell),
}

W_InputType.typedef = TypeDef(
    "StringI",
    __module__   = "cStringIO",
    __doc__      = "Simple type for treating strings as input file streams",
    closed       = GetSetProperty(descr_closed, cls=W_InputType),
    softspace    = GetSetProperty(descr_softspace,
                                  descr_setsoftspace,
                                  cls=W_InputType),
    **common_descrs
    # XXX CPython has the truncate() method here too, which is a bit strange
    )

W_OutputType.typedef = TypeDef(
    "StringO",
    __module__   = "cStringIO",
    __doc__      = "Simple type for output to strings.",
    truncate     = interp2app(W_OutputType.descr_truncate),
    write        = interp2app(W_OutputType.descr_write),
    writelines   = interp2app(W_OutputType.descr_writelines),
    closed       = GetSetProperty(descr_closed, cls=W_OutputType),
    softspace    = GetSetProperty(descr_softspace,
                                  descr_setsoftspace,
                                  cls=W_OutputType),
    **common_descrs
    )

# ____________________________________________________________

def StringIO(space, w_string=None):
    if space.is_none(w_string):
        return W_OutputType(space)
    else:
        string = space.getarg_w('s*', w_string).as_str()
        return W_InputType(space, string)
