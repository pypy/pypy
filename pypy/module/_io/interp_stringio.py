from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr, GetSetProperty)
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.module._io.interp_textio import (
        W_TextIOBase, W_IncrementalNewlineDecoder)
from pypy.module._io.interp_iobase import convert_size

class UnicodeIO(object):
    def __init__(self, data=None, pos=0):
        if data is None:
            data = []
        self.data = data
        self.pos = pos

    def resize(self, newlength):
        if len(self.data) > newlength:
            self.data = self.data[:newlength]
        if len(self.data) < newlength:
            self.data.extend([u'\0'] * (newlength - len(self.data)))

    def read(self, size):
        start = self.pos
        available = len(self.data) - start
        if available <= 0:
            return u''
        if size >= 0 and size <= available:
            end = start + size
        else:
            end = len(self.data)
        assert 0 <= start <= end
        self.pos = end
        return u''.join(self.data[start:end])

    def _convert_limit(self, limit):
        if limit < 0 or limit > len(self.data) - self.pos:
            limit = len(self.data) - self.pos
            if limit < 0:  # happens when self.pos > len(self.data)
                limit = 0
        return limit

    def readline_universal(self, limit):
        # Universal newline search. Find any of \r, \r\n, \n
        limit = self._convert_limit(limit)
        start = self.pos
        if start >= len(self.data):
            return u''
        end = start + limit
        pos = start
        while pos < end:
            ch = self.data[pos]
            pos += 1
            if ch == '\n':
                break
            if ch == '\r':
                if pos >= end:
                    break
                if self.data[pos] == '\n':
                    pos += 1
                    break
                else:
                    break
        self.pos = pos
        result = u''.join(self.data[start:pos])
        return result

    def readline(self, marker, limit):
        start = self.pos
        limit = self._convert_limit(limit)
        if start >= len(self.data):
            return u''
        end = start + limit
        found = False
        for pos in range(start, end - len(marker) + 1):
            ch = self.data[pos]
            if ch == marker[0]:
                for j in range(1, len(marker)):
                    if self.data[pos + j] != marker[j]:
                        break  # from inner loop
                else:
                    pos += len(marker)
                    found = True
                    break
        if not found:
            pos = end
        self.pos = pos
        result = u''.join(self.data[start:pos])
        return result

    def write(self, string):
        length = len(string)
        if self.pos + length > len(self.data):
            self.resize(self.pos + length)

        for i in range(length):
            self.data[self.pos + i] = string[i]
        self.pos += length

    def seek(self, pos):
        self.pos = pos

    def truncate(self, size):
        if size < len(self.data):
            self.resize(size)

    def getvalue(self):
        return u''.join(self.data)


class W_StringIO(W_TextIOBase):
    def __init__(self, space):
        W_TextIOBase.__init__(self, space)
        self.buf = UnicodeIO()

    @unwrap_spec(w_newline = WrappedDefault(u"\n"))
    def descr_init(self, space, w_initvalue=None, w_newline=None):
        # In case __init__ is called multiple times
        self.buf = UnicodeIO()
        self.w_decoder = None
        self.readnl = None
        self.writenl = None

        if space.is_w(w_newline, space.w_None):
            newline = None
        else:
            newline = space.unicode_w(w_newline)

        if (newline is not None and newline != u"" and newline != u"\n" and
                newline != u"\r" and newline != u"\r\n"):
            # Not using oefmt() because I don't know how to use it
            # with unicode
            raise OperationError(space.w_ValueError,
                space.mod(
                    space.newtext("illegal newline value: %s"), w_newline
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
                space.newint(int(self.readtranslate))
            )

        if not space.is_none(w_initvalue):
            self.write_w(space, w_initvalue)
            self.buf.pos = 0

    def descr_getstate(self, space):
        w_initialval = self.getvalue_w(space)
        w_dict = space.call_method(self.w_dict, "copy")
        if self.readnl is None:
            w_readnl = space.w_None
        else:
            w_readnl = space.str(space.newunicode(self.readnl))  # YYY
        return space.newtuple([
            w_initialval, w_readnl, space.newint(self.buf.pos), w_dict
        ])

    def descr_setstate(self, space, w_state):
        self._check_closed(space)

        # We allow the state tuple to be longer than 4, because we may need
        # someday to extend the object's state without breaking
        # backwards-compatibility
        if (not space.isinstance_w(w_state, space.w_tuple)
                or space.len_w(w_state) < 4):
            raise oefmt(space.w_TypeError,
                        "%T.__setstate__ argument should be a 4-tuple, got %T",
                        self, w_state)
        w_initval, w_readnl, w_pos, w_dict = space.unpackiterable(w_state, 4)
        if not space.isinstance_w(w_initval, space.w_unicode):
            raise oefmt(space.w_TypeError,
                        "unicode argument expected, got '%T'", w_initval)
        # Initialize state
        self.descr_init(space, None, w_readnl)

        # Restore the buffer state. We're not doing it via __init__
        # because the string value in the state tuple has already been
        # translated once by __init__. So we do not take any chance and replace
        # object's buffer completely
        initval = space.unicode_w(w_initval)
        pos = space.getindex_w(w_pos, space.w_TypeError)
        if pos < 0:
            raise oefmt(space.w_ValueError,
                        "position value cannot be negative")
        self.buf = UnicodeIO(list(initval), pos)
        if not space.is_w(w_dict, space.w_None):
            if not space.isinstance_w(w_dict, space.w_dict):
                raise oefmt(
                    space.w_TypeError,
                    "fourth item of state should be a dict, got a %T", w_dict)
            # Alternatively, we could replace the internal dictionary
            # completely. However, it seems more practical to just update it.
            space.call_method(self.w_dict, "update", w_dict)

    def _check_closed(self, space, message=None):
        if self.buf is None:
            if message is None:
                message = "I/O operation on closed file"
            raise OperationError(space.w_ValueError, space.newtext(message))

    def write_w(self, space, w_obj):
        if not space.isinstance_w(w_obj, space.w_unicode):
            raise oefmt(space.w_TypeError,
                        "unicode argument expected, got '%T'", w_obj)
        self._check_closed(space)
        orig_size = space.len_w(w_obj)

        if self.w_decoder is not None:
            w_decoded = space.call_method(
                self.w_decoder, "decode", w_obj, space.w_True)
        else:
            w_decoded = w_obj
        if self.writenl:
            w_decoded = space.call_method(
                w_decoded, "replace",
                space.newtext("\n"), space.newunicode(self.writenl))
        string = space.unicode_w(w_decoded)
        if string:
            self.buf.write(string)

        return space.newint(orig_size)

    def read_w(self, space, w_size=None):
        self._check_closed(space)
        size = convert_size(space, w_size)
        return space.newunicode(self.buf.read(size))

    def readline_w(self, space, w_limit=None):
        self._check_closed(space)
        limit = convert_size(space, w_limit)
        if self.readuniversal:
            result = self.buf.readline_universal(limit)
        else:
            if self.readtranslate:
                # Newlines are already translated, only search for \n
                newline = u'\n'
            else:
                newline = self.readnl
            result = self.buf.readline(newline, limit)
        return space.newunicode(result)


    @unwrap_spec(pos=int, mode=int)
    def seek_w(self, space, pos, mode=0):
        self._check_closed(space)

        if not 0 <= mode <= 2:
            raise oefmt(space.w_ValueError,
                        "Invalid whence (%d, should be 0, 1 or 2)", mode)
        elif mode == 0 and pos < 0:
            raise oefmt(space.w_ValueError, "negative seek position: %d", pos)
        elif mode != 0 and pos != 0:
            raise oefmt(space.w_IOError, "Can't do nonzero cur-relative seeks")

        # XXX: this makes almost no sense, but its how CPython does it.
        if mode == 1:
            pos = self.buf.pos
        elif mode == 2:
            pos = len(self.buf.data)
        assert pos >= 0
        self.buf.seek(pos)
        return space.newint(pos)

    def truncate_w(self, space, w_size=None):
        self._check_closed(space)
        if space.is_none(w_size):
            size = self.buf.pos
        else:
            size = space.int_w(w_size)
        if size < 0:
            raise oefmt(space.w_ValueError, "Negative size value %d", size)
        self.buf.truncate(size)
        return space.newint(size)

    def getvalue_w(self, space):
        self._check_closed(space)
        return space.newunicode(self.buf.getvalue())

    def readable_w(self, space):
        self._check_closed(space)
        return space.w_True

    def writable_w(self, space):
        self._check_closed(space)
        return space.w_True

    def seekable_w(self, space):
        self._check_closed(space)
        return space.w_True

    def close_w(self, space):
        self.buf = None

    def needs_finalizer(self):
        # 'self.buf = None' is not necessary when the object goes away
        return type(self) is not W_StringIO

    def closed_get_w(self, space):
        return space.newbool(self.buf is None)

    def line_buffering_get_w(self, space):
        return space.w_False

    def newlines_get_w(self, space):
        if self.w_decoder is None:
            return space.w_None
        return space.getattr(self.w_decoder, space.newtext("newlines"))


W_StringIO.typedef = TypeDef(
    '_io.StringIO', W_TextIOBase.typedef,
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
