from pypy.module._io.interp_iobase import W_IOBase
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, interp_attrproperty_w, interp_attrproperty,
    generic_new_descr)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rlib.rstring import UnicodeBuilder

STATE_ZERO, STATE_OK, STATE_DETACHED = range(3)

SEEN_CR   = 1
SEEN_LF   = 2
SEEN_CRLF = 4
SEEN_ALL  = SEEN_CR | SEEN_LF | SEEN_CRLF

class W_IncrementalNewlineDecoder(Wrappable):
    seennl = 0
    pendingcr = False
    w_decoder = None

    def __init__(self, space):
        self.w_newlines_dict = {
            SEEN_CR: space.wrap("\r"),
            SEEN_LF: space.wrap("\n"),
            SEEN_CRLF: space.wrap("\r\n"),
            SEEN_CR | SEEN_LF: space.newtuple(
                [space.wrap("\r"), space.wrap("\n")]),
            SEEN_CR | SEEN_CRLF: space.newtuple(
                [space.wrap("\r"), space.wrap("\r\n")]),
            SEEN_LF | SEEN_CRLF: space.newtuple(
                [space.wrap("\n"), space.wrap("\r\n")]),
            SEEN_CR | SEEN_LF | SEEN_CRLF: space.newtuple(
                [space.wrap("\r"), space.wrap("\n"), space.wrap("\r\n")]),
            }

    @unwrap_spec('self', ObjSpace, W_Root, int, W_Root)
    def descr_init(self, space, w_decoder, translate, w_errors=None):
        self.w_decoder = w_decoder
        self.translate = translate
        if space.is_w(w_errors, space.w_None):
            self.w_errors = space.wrap("strict")
        else:
            self.w_errors = w_errors

        self.seennl = 0
        pendingcr = False

    def newlines_get_w(space, self):
        return self.w_newlines_dict.get(self.seennl, space.w_None)

    @unwrap_spec('self', ObjSpace, W_Root, int)
    def decode_w(self, space, w_input, final=False):
        if self.w_decoder is None:
            raise OperationError(space.w_ValueError, space.wrap(
                "IncrementalNewlineDecoder.__init__ not called"))

        # decode input (with the eventual \r from a previous pass)
        if not space.is_w(self.w_decoder, space.w_None):
            w_output = space.call_method(self.w_decoder, "decode",
                                         w_input, space.wrap(final))
        else:
            w_output = w_input

        if not space.isinstance_w(w_output, space.w_unicode):
            raise OperationError(space.w_TypeError, space.wrap(
                "decoder should return a string result"))

        output = space.unicode_w(w_output)
        output_len = len(output)
        if self.pendingcr and (final or output_len):
            output = u'\r' + output
            self.pendingcr = False
            output_len += 1

        # retain last \r even when not translating data:
        # then readline() is sure to get \r\n in one pass
        if not final and output_len > 0:
            last = output_len - 1
            assert last >= 0
            if output[last] == u'\r':
                output = output[:last]
                self.pendingcr = True
                output_len -= 1

        if output_len == 0:
            return space.wrap(u"")

        # Record which newlines are read and do newline translation if
        # desired, all in one pass.
        seennl = self.seennl

        # If, up to now, newlines are consistently \n, do a quick check
        # for the \r
        only_lf = False
        if seennl == SEEN_LF or seennl == 0:
            only_lf = (output.find(u'\r') < 0)

        if only_lf:
            # If not already seen, quick scan for a possible "\n" character.
            # (there's nothing else to be done, even when in translation mode)
            if seennl == 0 and output.find(u'\n') >= 0:
                seennl |= SEEN_LF
                # Finished: we have scanned for newlines, and none of them
                # need translating.
        elif not self.translate:
            i = 0
            while i < output_len:
                if seennl == SEEN_ALL:
                    break
                c = output[i]
                i += 1
                if c == u'\n':
                    seennl |= SEEN_LF
                elif c == u'\r':
                    if i < output_len and output[i] == u'\n':
                        seennl |= SEEN_CRLF
                        i += 1
                    else:
                        seennl |= SEEN_CR
        elif output.find(u'\r') >= 0:
            # Translate!
            builder = UnicodeBuilder(output_len)
            i = 0
            while i < output_len:
                c = output[i]
                i += 1
                if c == u'\n':
                    seennl |= SEEN_LF
                elif c == u'\r':
                    if i < output_len and output[i] == u'\n':
                        seennl |= SEEN_CRLF
                        i += 1
                    else:
                        seennl |= SEEN_CR
                    builder.append(u'\n')
                    continue
                builder.append(c)
            output = builder.build()

        self.seennl |= seennl
        return space.wrap(output)

    @unwrap_spec('self', ObjSpace)
    def reset_w(self, space):
        self.seennl = 0
        self.pendingcr = False
        if self.w_decoder and not space.is_w(self.w_decoder, space.w_None):
            space.call_method(self.w_decoder, "reset")

    @unwrap_spec('self', ObjSpace)
    def getstate_w(self, space):
        if self.w_decoder and not space.is_w(self.w_decoder, space.w_None):
            w_state = space.call_method(self.w_decoder, "getstate")
            w_buffer, w_flag = space.unpackiterable(w_state, 2)
            flag = space.r_longlong_w(w_flag)
        else:
            w_buffer = space.wrap("")
            flag = 0
        flag <<= 1
        if self.pendingcr:
            flag |= 1
        return space.newtuple([w_buffer, space.wrap(flag)])

    @unwrap_spec('self', ObjSpace, W_Root)
    def setstate_w(self, space, w_state):
        w_buffer, w_flag = space.unpackiterable(w_state, 2)
        flag = space.r_longlong_w(w_flag)
        self.pendingcr = (flag & 1)
        flag >>= 1

        if self.w_decoder and not space.is_w(self.w_decoder, space.w_None):
            w_state = space.newtuple([w_buffer, space.wrap(flag)])
            space.call_method(self.w_decoder, "setstate", w_state)

W_IncrementalNewlineDecoder.typedef = TypeDef(
    'TextIOWrapper',
    __new__ = generic_new_descr(W_IncrementalNewlineDecoder),
    __init__  = interp2app(W_IncrementalNewlineDecoder.descr_init),

    decode = interp2app(W_IncrementalNewlineDecoder.decode_w),
    reset = interp2app(W_IncrementalNewlineDecoder.reset_w),
    getstate = interp2app(W_IncrementalNewlineDecoder.getstate_w),
    setstate = interp2app(W_IncrementalNewlineDecoder.setstate_w),

    newlines = GetSetProperty(W_IncrementalNewlineDecoder.newlines_get_w),
    )

class W_TextIOBase(W_IOBase):
    w_encoding = None

    def __init__(self, space):
        W_IOBase.__init__(self, space)

    def _unsupportedoperation(self, space, message):
        w_exc = space.getattr(space.getbuiltinmodule('_io'),
                              space.wrap('UnsupportedOperation'))
        raise OperationError(w_exc, space.wrap(message))

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._unsupportedoperation(space, "read")

    @unwrap_spec('self', ObjSpace, W_Root)
    def readline_w(self, space, w_limit=None):
        self._unsupportedoperation(space, "readline")

W_TextIOBase.typedef = TypeDef(
    '_TextIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_TextIOBase),

    read = interp2app(W_TextIOBase.read_w),
    encoding = interp_attrproperty_w("w_encoding", W_TextIOBase)
    )

class W_TextIOWrapper(W_TextIOBase):
    def __init__(self, space):
        W_TextIOBase.__init__(self, space)
        self.state = STATE_ZERO

    @unwrap_spec('self', ObjSpace, W_Root, W_Root, W_Root, W_Root, int)
    def descr_init(self, space, w_buffer, w_encoding=None,
                   w_errors=None, w_newline=None, line_buffering=0):
        self.state = STATE_ZERO

        self.w_buffer = w_buffer

        # Set encoding
        self.w_encoding = None
        if space.is_w(w_encoding, space.w_None):
            try:
                w_locale = space.call_method(space.builtin, '__import__',
                                             space.wrap("locale"))
                self.w_encoding = space.call_method(w_locale,
                                                    "getpreferredencoding")
            except OperationError, e:
                # getpreferredencoding() may also raise ImportError
                if not e.match(space, space.w_ImportError):
                    raise
                self.w_encoding = space.wrap("ascii")
        if self.w_encoding:
            pass
        elif not space.is_w(w_encoding, space.w_None):
            self.w_encoding = w_encoding
        else:
            raise OperationError(space.w_IOError, space.wrap(
                "could not determine default encoding"))

        if space.is_w(w_newline, space.w_None):
            newline = None
        else:
            newline = space.str_w(w_newline)
        if newline and newline not in ('\n', '\r\n', '\r'):
            raise OperationError(space.w_ValueError, space.wrap(
                "illegal newline value: %s" % (newline,)))

        self.line_buffering = line_buffering

        self.state = STATE_OK

    def _check_init(self, space):
        if self.state == STATE_ZERO:
            raise OperationError(space.w_ValueError, space.wrap(
                "I/O operation on uninitialized object"))
        elif self.state == STATE_DETACHED:
            raise OperationError(space.w_ValueError, space.wrap(
                "underlying buffer has been detached"))

    @unwrap_spec('self', ObjSpace)
    def readable_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_buffer, "readable")

    @unwrap_spec('self', ObjSpace)
    def writable_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_buffer, "writable")

    @unwrap_spec('self', ObjSpace)
    def seekable_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_buffer, "seekable")

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        # XXX w_size?
        w_bytes = space.call_method(self.w_buffer, "read")
        return space.call_method(w_bytes, "decode", self.w_encoding)

    @unwrap_spec('self', ObjSpace, W_Root)
    def readline_w(self, space, w_limit=None):
        # XXX w_limit?
        w_bytes = space.call_method(self.w_buffer, "readline")
        return space.call_method(w_bytes, "decode", self.w_encoding)

W_TextIOWrapper.typedef = TypeDef(
    'TextIOWrapper', W_TextIOBase.typedef,
    __new__ = generic_new_descr(W_TextIOWrapper),
    __init__  = interp2app(W_TextIOWrapper.descr_init),

    read = interp2app(W_TextIOWrapper.read_w),
    readline = interp2app(W_TextIOWrapper.readline_w),

    line_buffering = interp_attrproperty("line_buffering", W_TextIOWrapper),
    readable = interp2app(W_TextIOWrapper.readable_w),
    writable = interp2app(W_TextIOWrapper.writable_w),
    seekable = interp2app(W_TextIOWrapper.seekable_w),
    )
