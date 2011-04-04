from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr, GetSetProperty)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.module._io.interp_textio import W_TextIOBase, W_IncrementalNewlineDecoder
from pypy.module._io.interp_iobase import convert_size


class W_StringIO(W_TextIOBase):
    def __init__(self, space):
        W_TextIOBase.__init__(self, space)
        self.buf = []
        self.pos = 0

    def descr_init(self, space, w_initvalue=None, w_newline="\n"):
        # In case __init__ is called multiple times
        self.buf = []
        self.pos = 0
        self.w_decoder = None
        self.readnl = None
        self.writenl = None

        if space.is_w(w_newline, space.w_None):
            newline = None
        else:
            newline = space.unicode_w(w_newline)

        if (newline is not None and newline != u"" and newline != u"\n" and
            newline != u"\r" and newline != u"\r\n"):
            # Not using operationerrfmt() because I don't know how to ues it
            # with unicode
            raise OperationError(space.w_ValueError,
                space.mod(
                    space.wrap("illegal newline value: %s"), space.wrap(newline)
                )
            )
        if newline is not None:
            self.readnl = newline
        self.readuniversal = newline is None or newline == u""
        self.readtranslate = newline is None
        if newline and newline[0] == u"\r":
            self.writenl = newline
        if self.readuniversal:
            self.w_decoder = space.call_function(
                space.gettypefor(W_IncrementalNewlineDecoder),
                space.w_None,
                space.wrap(int(self.readtranslate))
            )

        if not space.is_w(w_initvalue, space.w_None):
            self.write_w(space, w_initvalue)
            self.pos = 0

    def descr_getstate(self, space):
        w_initialval = self.getvalue_w(space)
        w_dict = space.call_method(self.w_dict, "copy")
        if self.readnl is None:
            w_readnl = space.w_None
        else:
            w_readnl = space.str(space.wrap(self.readnl))
        return space.newtuple([
            w_initialval, w_readnl, space.wrap(self.pos), w_dict
        ])

    def descr_setstate(self, space, w_state):
        self._check_closed(space)

        # We allow the state tuple to be longer than 4, because we may need
        # someday to extend the object's state without breaking
        # backwards-compatibility
        if not space.isinstance_w(w_state, space.w_tuple) or space.len_w(w_state) < 4:
            raise operationerrfmt(space.w_TypeError,
                "%s.__setstate__ argument should be a 4-tuple, got %s",
                space.type(self).getname(space),
                space.type(w_state).getname(space)
            )
        w_initval, w_readnl, w_pos, w_dict = space.unpackiterable(w_state, 4)
        # Initialize state
        self.descr_init(space, w_initval, w_readnl)

        # Restore the buffer state. Even if __init__ did initialize the buffer,
        # we have to initialize it again since __init__ may translates the
        # newlines in the inital_value string. We clearly do not want that
        # because the string value in the state tuple has already been
        # translated once by __init__. So we do not take any chance and replace
        # object's buffer completely
        initval = space.unicode_w(w_initval)
        size = len(initval)
        self.resize_buffer(size)
        self.buf = [c for c in initval]
        pos = space.getindex_w(w_pos, space.w_TypeError)
        if pos < 0:
            raise OperationError(space.w_ValueError,
                space.wrap("position value cannot be negative")
            )
        self.pos = pos
        if not space.is_w(w_dict, space.w_None):
            if not space.isinstance_w(w_dict, space.w_dict):
                raise operationerrfmt(space.w_TypeError,
                    "fourth item of state should be a dict, got a %s",
                    space.type(w_dict).getname(space)
                )
            # Alternatively, we could replace the internal dictionary
            # completely. However, it seems more practical to just update it.
            space.call_method(self.w_dict, "update", w_dict)

    def _check_closed(self, space, message=None):
        if self.buf is None:
            if message is None:
                message = "I/O operation on closed file"
            raise OperationError(space.w_ValueError, space.wrap(message))

    def resize_buffer(self, newlength):
        if len(self.buf) > newlength:
            self.buf = self.buf[:newlength]
        if len(self.buf) < newlength:
            self.buf.extend([u'\0'] * (newlength - len(self.buf)))

    def write(self, string):
        length = len(string)
        if self.pos + length > len(self.buf):
            self.resize_buffer(self.pos + length)

        for i in range(length):
            self.buf[self.pos + i] = string[i]
        self.pos += length

    def write_w(self, space, w_obj):
        if not space.isinstance_w(w_obj, space.w_unicode):
            raise operationerrfmt(space.w_TypeError,
                                  "string argument expected, got '%s'",
                                  space.type(w_obj).getname(space, '?'))
        self._check_closed(space)

        orig_size = space.len_w(w_obj)

        if self.w_decoder is not None:
            w_decoded = space.call_method(
                self.w_decoder, "decode", w_obj, space.w_True
            )
        else:
            w_decoded = w_obj

        if self.writenl:
            w_decoded = space.call_method(
                w_decoded, "replace", space.wrap("\n"), space.wrap(self.writenl)
            )

        string = space.unicode_w(w_decoded)
        size = len(string)

        if size:
            self.write(string)
        return space.wrap(orig_size)

    def read_w(self, space, w_size=None):
        self._check_closed(space)
        size = convert_size(space, w_size)
        start = self.pos
        available = len(self.buf) - start
        if available <= 0:
            return space.wrap(u"")
        if size >= 0 and size <= available:
            end = start + size
        else:
            end = len(self.buf)
        assert 0 <= start <= end
        self.pos = end
        return space.wrap(u''.join(self.buf[start:end]))

    @unwrap_spec(limit=int)
    def readline_w(self, space, limit=-1):
        self._check_closed(space)

        if self.pos >= len(self.buf):
            return space.wrap(u"")

        start = self.pos
        if limit < 0 or limit > len(self.buf) - self.pos:
            limit = len(self.buf) - self.pos

        assert limit >= 0
        end = start + limit

        endpos, consumed = self._find_line_ending(
            # XXX: super inefficient, makes a copy of the entire contents.
            u"".join(self.buf),
            start,
            end
        )
        if endpos >= 0:
            endpos += start
        else:
            endpos = end
        assert endpos >= 0
        self.pos = endpos
        return space.wrap(u"".join(self.buf[start:endpos]))

    @unwrap_spec(pos=int, mode=int)
    def seek_w(self, space, pos, mode=0):
        self._check_closed(space)

        if not 0 <= mode <= 2:
            raise operationerrfmt(space.w_ValueError,
                "Invalid whence (%d, should be 0, 1 or 2)", mode
            )
        elif mode == 0 and pos < 0:
            raise operationerrfmt(space.w_ValueError,
                "negative seek position: %d", pos
            )
        elif mode != 0 and pos != 0:
            raise OperationError(space.w_IOError,
                space.wrap("Can't do nonzero cur-relative seeks")
            )

        # XXX: this makes almost no sense, but its how CPython does it.
        if mode == 1:
            pos = self.pos
        elif mode == 2:
            pos = len(self.buf)

        assert pos >= 0
        self.pos = pos
        return space.wrap(pos)

    def truncate_w(self, space, w_size=None):
        self._check_closed(space)
        if space.is_w(w_size, space.w_None):
            size = self.pos
        else:
            size = space.int_w(w_size)

        if size < 0:
            raise operationerrfmt(space.w_ValueError,
                "Negative size value %d", size
            )

        if size < len(self.buf):
            self.resize_buffer(size)

        return space.wrap(size)

    def getvalue_w(self, space):
        self._check_closed(space)
        return space.wrap(u''.join(self.buf))

    def readable_w(self, space):
        return space.w_True

    def writable_w(self, space):
        return space.w_True

    def seekable_w(self, space):
        return space.w_True

    def close_w(self, space):
        self.buf = None

    def closed_get_w(self, space):
        return space.wrap(self.buf is None)

    def line_buffering_get_w(self, space):
        return space.w_False

    def newlines_get_w(self, space):
        if self.w_decoder is None:
            return space.w_None
        return space.getattr(self.w_decoder, space.wrap("newlines"))


W_StringIO.typedef = TypeDef(
    'StringIO', W_TextIOBase.typedef,
    __module__ = "_io",
    __new__  = generic_new_descr(W_StringIO),
    __init__ = interp2app(W_StringIO.descr_init),
    __getstate__ = interp2app(W_StringIO.descr_getstate),
    __setstate__ = interp2app(W_StringIO.descr_setstate),
    write = interp2app(W_StringIO.write_w),
    read = interp2app(W_StringIO.read_w),
    readline = interp2app(W_StringIO.readline_w),
    seek = interp2app(W_StringIO.seek_w),
    truncate = interp2app(W_StringIO.truncate_w),
    getvalue = interp2app(W_StringIO.getvalue_w),
    readable = interp2app(W_StringIO.readable_w),
    writable = interp2app(W_StringIO.writable_w),
    seekable = interp2app(W_StringIO.seekable_w),
    close = interp2app(W_StringIO.close_w),
    closed = GetSetProperty(W_StringIO.closed_get_w),
    line_buffering = GetSetProperty(W_StringIO.line_buffering_get_w),
    newlines = GetSetProperty(W_StringIO.newlines_get_w),
)
