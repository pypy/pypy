from pypy.interpreter.typedef import TypeDef, generic_new_descr
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.module._io.interp_textio import W_TextIOBase
from pypy.module._io.interp_iobase import convert_size

class W_StringIO(W_TextIOBase):
    def __init__(self, space):
        W_TextIOBase.__init__(self, space)
        self.buf = []
        self.pos = 0

    def _check_closed(self, space, message=None):
        pass
    def _check_initialized(self):
        pass

    @unwrap_spec('self', ObjSpace, W_Root)
    def descr_init(self, space, w_initvalue=None):
        # In case __init__ is called multiple times
        self.buf = []
        self.pos = 0

        if not space.is_w(w_initvalue, space.w_None):
            self.write_w(space, w_initvalue)
            self.pos = 0

    def resize_buffer(self, newlength):
        if len(self.buf) > newlength:
            self.buf = self.buf[:newlength]
        if len(self.buf) < newlength:
            self.buf.extend([u'\0'] * (newlength - len(self.buf)))

    def write(self, string):
        # XXX self.decoder
        decoded = string
        # XXX writenl

        length = len(decoded)
        if self.pos + length > len(self.buf):
            self.resize_buffer(self.pos + length)

        for i in range(length):
            self.buf[self.pos + i] = string[i]
        self.pos += length

    @unwrap_spec('self', ObjSpace, W_Root)
    def write_w(self, space, w_obj):
        self._check_initialized()
        if not space.isinstance_w(w_obj, space.w_unicode):
            raise operationerrfmt(space.w_TypeError,
                                  "string argument expected, got '%s'",
                                  space.type(self).getname(space, '?'))
        self._check_closed(space)
        string = space.unicode_w(w_obj)
        size = len(string)
        if size:
            self.write(string)
        return space.wrap(size)

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        size = convert_size(space, w_size)
        start = self.pos
        if size >= 0:
            end = start + size
        else:
            end = len(self.buf)
        self.pos = end
        return space.wrap(u''.join(self.buf[start:end]))

    @unwrap_spec('self', ObjSpace)
    def getvalue_w(self, space):
        self._check_initialized()
        self._check_closed(space)
        return space.wrap(u''.join(self.buf))

W_StringIO.typedef = TypeDef(
    'StringIO', W_TextIOBase.typedef,
    __new__  = generic_new_descr(W_StringIO),
    __init__ = interp2app(W_StringIO.descr_init),
    write=interp2app(W_StringIO.write_w),
    read=interp2app(W_StringIO.read_w),
    getvalue=interp2app(W_StringIO.getvalue_w),
    )

