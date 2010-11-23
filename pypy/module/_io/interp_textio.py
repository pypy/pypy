from pypy.module._io.interp_iobase import W_IOBase
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, interp_attrproperty_w, interp_attrproperty,
    generic_new_descr)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rlib.rstring import UnicodeBuilder
from pypy.rlib.rarithmetic import r_ulonglong
from pypy.module._codecs import interp_codecs
from pypy.module._io.interp_iobase import convert_size
import sys

STATE_ZERO, STATE_OK, STATE_DETACHED = range(3)

SEEN_CR   = 1
SEEN_LF   = 2
SEEN_CRLF = 4
SEEN_ALL  = SEEN_CR | SEEN_LF | SEEN_CRLF

_WINDOWS = sys.platform == 'win32'

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

    @unwrap_spec('self', ObjSpace, W_Root)
    def write_w(self, space, w_data):
        self._unsupportedoperation(space, "write")

    @unwrap_spec('self', ObjSpace)
    def detach_w(self, space):
        self._unsupportedoperation(space, "detach")

W_TextIOBase.typedef = TypeDef(
    '_TextIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_TextIOBase),

    read = interp2app(W_TextIOBase.read_w),
    readline = interp2app(W_TextIOBase.readline_w),
    detach = interp2app(W_TextIOBase.detach_w),
    encoding = interp_attrproperty_w("w_encoding", W_TextIOBase)
    )

class PositionCookie:
    pass

class W_TextIOWrapper(W_TextIOBase):
    def __init__(self, space):
        W_TextIOBase.__init__(self, space)
        self.state = STATE_ZERO
        self.w_decoder = None

        self.decoded_chars = None   # buffer for text returned from decoder
        self.decoded_chars_used = 0 # offset into _decoded_chars for read()
        self.pending_bytes = None   # list of bytes objects waiting to be
                                    # written, or NULL
        self.chunk_size = 8192

        self.readuniversal = False
        self.readtranslate = False
        self.readnl = None

        self.encodefunc = None # Specialized encoding func (see below)
        self.encoding_start_of_stream = False # Whether or not it's the start
                                              # of the stream

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

        if space.is_w(w_errors, space.w_None):
            w_errors = space.wrap("strict")

        if space.is_w(w_newline, space.w_None):
            newline = None
        else:
            newline = space.unicode_w(w_newline)
        if newline and newline not in (u'\n', u'\r\n', u'\r'):
            r = space.str_w(space.repr(w_newline))
            raise OperationError(space.w_ValueError, space.wrap(
                "illegal newline value: %s" % (r,)))

        self.line_buffering = line_buffering

        self.readuniversal = not newline # null or empty
        self.readtranslate = newline is None
        self.readnl = newline

        self.writetranslate = (newline != u'')
        if not self.readuniversal:
            self.writenl = self.readnl
            if self.writenl == u'\n':
                self.writenl = None
        elif _WINDOWS:
            self.writenl = u"\r\n"

        # build the decoder object
        if space.is_true(space.call_method(w_buffer, "readable")):
            w_codec = interp_codecs.lookup_codec(space,
                                                 space.str_w(self.w_encoding))
            self.w_decoder = space.call_method(w_codec,
                                               "incrementaldecoder", w_errors)
            if self.readuniversal:
                self.w_decoder = space.call_function(
                    space.gettypeobject(W_IncrementalNewlineDecoder.typedef),
                    self.w_decoder, space.wrap(self.readtranslate))

        # build the encoder object
        if space.is_true(space.call_method(w_buffer, "writable")):
            w_codec = interp_codecs.lookup_codec(space,
                                                 space.str_w(self.w_encoding))
            self.w_encoder = space.call_method(w_codec,
                                               "incrementalencoder", w_errors)

        self.seekable = space.is_true(space.call_method(w_buffer, "seekable"))
        self.telling = self.seekable

        self.state = STATE_OK

    def _check_init(self, space):
        if self.state == STATE_ZERO:
            raise OperationError(space.w_ValueError, space.wrap(
                "I/O operation on uninitialized object"))
        elif self.state == STATE_DETACHED:
            raise OperationError(space.w_ValueError, space.wrap(
                "underlying buffer has been detached"))

    def _check_closed(self, space, message=None):
        self._check_init(space)
        W_TextIOBase._check_closed(self, space, message)

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

    @unwrap_spec('self', ObjSpace)
    def fileno_w(self, space):
        self._check_init(space)
        return space.call_method(self.w_buffer, "fileno")

    @unwrap_spec('self', ObjSpace)
    def flush_w(self, space):
        self._check_closed(space)
        self.telling = self.seekable
        self._writeflush(space)
        space.call_method(self.w_buffer, "flush")

    @unwrap_spec('self', ObjSpace)
    def close_w(self, space):
        self._check_init(space)
        if not self._closed(space):
            return space.call_method(self, "flush")
            return space.call_method(self.w_buffer, "close")

    # _____________________________________________________________
    # read methods

    def _set_decoded_chars(self, chars):
        self.decoded_chars = chars
        self.decoded_chars_used = 0

    def _get_decoded_chars(self, size):
        if self.decoded_chars is None:
            return u""

        available = len(self.decoded_chars) - self.decoded_chars_used
        if size < 0 or size > available:
            size = available
        assert size >= 0

        if self.decoded_chars_used > 0 or size < available:
            start = self.decoded_chars_used
            end = self.decoded_chars_used + size
            assert start >= 0
            assert end >= 0
            chars = self.decoded_chars[start:end]
        else:
            chars = self.decoded_chars

        self.decoded_chars_used += size
        return chars

    def _read_chunk(self, space):
        """Read and decode the next chunk of data from the BufferedReader.
        The return value is True unless EOF was reached.  The decoded string
        is placed in self._decoded_chars (replacing its previous value).
        The entire input chunk is sent to the decoder, though some of it may
        remain buffered in the decoder, yet to be converted."""

        if not self.w_decoder:
            raise OperationError(space.w_IOError, space.wrap("not readable"))

        # XXX
        # if self.telling...

        # Read a chunk, decode it, and put the result in self._decoded_chars
        w_input = space.call_method(self.w_buffer, "read1",
                                    space.wrap(self.chunk_size))
        eof = space.int_w(space.len(w_input)) == 0
        w_decoded = space.call_method(self.w_decoder, "decode",
                                      w_input, space.wrap(eof))
        self._set_decoded_chars(space.unicode_w(w_decoded))
        if space.int_w(space.len(w_decoded)) > 0:
            eof = False

        # XXX
        # if self.telling...

        return not eof

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._check_closed(space)
        if not self.w_decoder:
            raise OperationError(space.w_IOError, space.wrap("not readable"))

        size = convert_size(space, w_size)
        if size < 0:
            # Read everything
            w_bytes = space.call_method(self.w_buffer, "read")
            w_decoded = space.call_method(self.w_decoder, "decode", w_bytes)
            w_result = space.wrap(self._get_decoded_chars(-1))
            w_final = space.add(w_result, w_decoded)
            self.snapshot = None
            return w_final

        remaining = size
        builder = UnicodeBuilder(size)

        # Keep reading chunks until we have n characters to return
        while True:
            data = self._get_decoded_chars(remaining)
            builder.append(data)
            remaining -= len(data)

            if remaining <= 0: # Done
                break

            if not self._read_chunk(space):
                # EOF
                break

        return space.wrap(builder.build())

    def _find_line_ending(self, line, start):
        end = len(line)
        size = end - start
        if self.readtranslate:

            # Newlines are already translated, only search for \n
            pos = line.find(u'\n', start, end)
            if pos >= 0:
                return pos - start + 1, 0
            else:
                return -1, size
        elif self.readuniversal:
            # Universal newline search. Find any of \r, \r\n, \n
            # The decoder ensures that \r\n are not split in two pieces
            i = 0
            while True:
                # Fast path for non-control chars. The loop always ends
                # since the Py_UNICODE storage is NUL-terminated.
                while line[start + i] > '\r':
                    i += 1
                if i >= size:
                    return -1, size
                ch = line[start + i]
                i += 1
                if ch == '\n':
                    return i, 0
                if ch == '\r':
                    if line[start + i] == '\n':
                        return i + 1, 0
                    else:
                        return i, 0
        else:
            # Non-universal mode.
            pos = line.find(self.readnl, start, end)
            if pos >= 0:
                return pos - start + len(self.readnl), 0
            else:
                restart = end - len(self.readnl)
                if restart >= 0:
                    pos = line.find(self.readnl[0], restart, end)
                    if pos >= 0:
                        return -1, pos - start
                return -1, size

    @unwrap_spec('self', ObjSpace, W_Root)
    def readline_w(self, space, w_limit=None):
        self._check_closed(space)
        self._writeflush(space)

        limit = convert_size(space, w_limit)
        chunked = 0

        line = None
        remaining = None
        chunks = []

        while True:
            # First, get some data if necessary
            has_data = True
            while not self.decoded_chars:
                if not self._read_chunk(space):
                    has_data = False
                    break
            if not has_data:
                # end of file
                self._set_decoded_chars(None)
                self.snapshot = None
                start = endpos = offset_to_buffer = 0
                break

            if not remaining:
                line = self.decoded_chars
                start = self.decoded_chars_used
                offset_to_buffer = 0
            else:
                assert self.decoded_chars_used == 0
                line = remaining + self.decoded_chars
                start = 0
                offset_to_buffer = len(remaining)
                remaining = None

            line_len = len(line)
            endpos, consumed = self._find_line_ending(line, start)
            if endpos >= 0:
                endpos += start
                if limit >= 0 and endpos >= start + limit - chunked:
                    endpos = start + limit - chunked
                    assert endpos >= 0
                break
            assert consumed >= 0

            # We can put aside up to `endpos`
            endpos = consumed + start
            if limit >= 0 and endpos >= start + limit - chunked:
                # Didn't find line ending, but reached length limit
                endpos = start + limit - chunked
                assert endpos >= 0
                break

            # No line ending seen yet - put aside current data
            if endpos > start:
                s = line[start:endpos]
                chunks.append(s)
                chunked += len(s)
            # There may be some remaining bytes we'll have to prepend to the
            # next chunk of data
            if endpos < line_len:
                remaining = line[endpos:]
            line = None
            # We have consumed the buffer
            self._set_decoded_chars(None)

        if line:
            # Our line ends in the current buffer
            decoded_chars_used = endpos - offset_to_buffer
            assert decoded_chars_used >= 0
            self.decoded_chars_used = decoded_chars_used
            if start > 0 or endpos < len(line):
                line = line[start:endpos]
        if remaining:
            chunks.append(remaining)
            remaining = None
        if chunks:
            if line:
                chunks.append(line)
            line = u''.join(chunks)

        if line:
            return space.wrap(line)
        else:
            return space.wrap(u'')

    # _____________________________________________________________
    # write methods

    @unwrap_spec('self', ObjSpace, W_Root)
    def write_w(self, space, w_text):
        self._check_init(space)
        self._check_closed(space)

        if not self.w_encoder:
            raise OperationError(space.w_IOError, space.wrap("not writable"))

        text = space.unicode_w(w_text)
        textlen = len(text)

        haslf = False
        if (self.writetranslate and self.writenl) or self.line_buffering:
            if text.find(u'\n') >= 0:
                haslf = True
        if haslf and self.writetranslate and self.writenl:
            w_text = space.call_method(w_text, "replace", space.wrap(u'\n'),
                                       space.wrap(self.writenl))
            text = space.unicode_w(w_text)

        needflush = False
        if self.line_buffering and (haslf or text.find(u'\r') >= 0):
            needflush = True

        # XXX What if we were just reading?
        if self.encodefunc:
            w_bytes = self.encodefunc(space, w_text, self.errors)
            self.encoding_start_of_stream = False
        else:
            w_bytes = space.call_method(self.w_encoder, "encode", w_text)

        b = space.str_w(w_bytes)
        if not self.pending_bytes:
            self.pending_bytes = []
            self.pending_bytes_count = 0
        self.pending_bytes.append(b)
        self.pending_bytes_count += len(b)

        if self.pending_bytes_count > self.chunk_size or needflush:
            self._writeflush(space)

        if needflush:
            space.call_method(self.w_buffer, "flush")

        self.snapshot = None

        if self.w_decoder:
            space.call_method(self.w_decoder, "reset")

        return space.wrap(textlen)

    def _writeflush(self, space):
        if not self.pending_bytes:
            return

        pending_bytes = ''.join(self.pending_bytes)
        self.pending_bytes = None

        space.call_method(self.w_buffer, "write", space.wrap(pending_bytes))

    @unwrap_spec('self', ObjSpace)
    def detach_w(self, space):
        self._check_init(space)
        space.call_method(self, "flush")
        w_buffer = self.w_buffer
        self.w_buffer = None
        self.state = STATE_DETACHED
        return w_buffer

    # _____________________________________________________________
    # seek/tell

    def _pack_cookie(self, start_pos, dec_flags=0,
                           bytes_to_feed=0, need_eof=0, chars_to_skip=0):
        # The meaning of a tell() cookie is: seek to position, set the
        # decoder flags to dec_flags, read bytes_to_feed bytes, feed them
        # into the decoder with need_eof as the EOF flag, then skip
        # chars_to_skip characters of the decoded result.  For most simple
        # decoders, tell() will often just give a byte offset in the file.
        return (start_pos | (dec_flags<<64) | (bytes_to_feed<<128) |
               (chars_to_skip<<192) | bool(need_eof)<<256)

    def _unpack_cookie(self, bigint):
        cookie = PositionCookie()
        cookie.start_pos = bigint.ulonglongmask()
        bigint = bigint.rshift(r_ulonglong.BITS)
        cookie.dec_flags = 0
        cookie.bytes_to_feed = 0
        cookie.chars_to_skip = 0
        cookie.need_eof = 0
        return cookie

    def _decoder_setstate(self, space, cookie):
        # When seeking to the start of the stream, we call decoder.reset()
        # rather than decoder.getstate().
        # This is for a few decoders such as utf-16 for which the state value
        # at start is not (b"", 0) but e.g. (b"", 2) (meaning, in the case of
        # utf-16, that we are expecting a BOM).
        if cookie.start_pos == 0 and cookie.dec_flags == 0:
            space.call_method(self.w_decoder, "reset")
            self.encoding_start_of_stream = True
        else:
            space.call_method(self.w_encoder, "setstate",
                              space.newtuple([space.wrap(""),
                                              space.wrap(cookie.dec_flags)]))

    def _encoder_setstate(self, space, cookie):
        if cookie.start_pos == 0 and cookie.dec_flags == 0:
            space.call_method(self.w_encoder, "reset")
            self.encoding_start_of_stream = True
        else:
            space.call_method(self.w_encoder, "setstate", space.wrap(0))
            self.encoding_start_of_stream = False

    @unwrap_spec('self', ObjSpace, W_Root, int)
    def seek_w(self, space, w_pos, whence=0):
        self._check_closed(space)

        if not self.seekable:
            raise OperationError(space.w_IOError, space.wrap(
                "underlying stream is not seekable"))

        if whence == 1:
            # seek relative to current position
            if not space.is_true(space.eq(w_pos, space.wrap(0))):
                raise OperationError(space.w_IOError, space.wrap(
                    "can't do nonzero cur-relative seeks"))
            # Seeking to the current position should attempt to sync the
            # underlying buffer with the current position.
            w_pos = space.call_method(self, "tell")

        elif whence == 2:
            # seek relative to end of file
            if not space.is_true(space.eq(w_pos, space.wrap(0))):
                raise OperationError(space.w_IOError, space.wrap(
                    "can't do nonzero end-relative seeks"))
            space.call_method(self, "flush")
            self._set_decoded_chars(None)
            self.snapshot = None
            if self.w_decoder:
                space.call_method(self.w_decoder, "reset")
            return space.call_method(self.w_buffer, "seek",
                                     w_pos, space.wrap(whence))

        elif whence != 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "invalid whence (%d, should be 0, 1 or 2)" % (whence,)))

        if space.is_true(space.lt(w_pos, space.wrap(0))):
            r = space.str_w(space.repr(w_pos))
            raise OperationError(space.w_ValueError, space.wrap(
                "negative seek position %s" % (r,)))

        space.call_method(self, "flush")

        # The strategy of seek() is to go back to the safe start point and
        # replay the effect of read(chars_to_skip) from there.
        cookie = self._unpack_cookie(space.bigint_w(w_pos))

        # Seek back to the safe start point
        space.call_method(self.w_buffer, "seek", space.wrap(cookie.start_pos))

        self._set_decoded_chars(None)
        self.snapshot = None

        # Restore the decoder to its state from the safe start point.
        if self.w_decoder:
            self._decoder_setstate(space, cookie)

        if cookie.chars_to_skip:
            # Just like _read_chunk, feed the decoder and save a snapshot.
            w_chunk = space.call_method(self.w_buffer, "read",
                                        space.wrap(cookie.chars_to_feed))
            # XXX self.snapshot = cookie.dec_flags, w_chunk

            w_decoded = space.call_method(self.w_decoder, "decode",
                                          w_chunk, space.wrap(cookie.need_eof))
            self._set_decoded_chars(space.unicode_w(w_decoded))

            # Skip chars_to_skip of the decoded characters
            if len(self.decoded_chars) < cookie.chars_to_skip:
                raise OperationError(space.w_IOError, space.wrap(
                    "can't restore logical file position"))
            self.decoded_chars_used = cookie.chars_to_skip
        else:
            # XXX self.snapshot = cookie.dec_flags, space.wrap(u"")
            pass

        # Finally, reset the encoder (merely useful for proper BOM handling)
        if self.w_encoder:
            self._encoder_setstate(space, cookie)

        return w_pos


W_TextIOWrapper.typedef = TypeDef(
    'TextIOWrapper', W_TextIOBase.typedef,
    __new__ = generic_new_descr(W_TextIOWrapper),
    __init__  = interp2app(W_TextIOWrapper.descr_init),

    read = interp2app(W_TextIOWrapper.read_w),
    readline = interp2app(W_TextIOWrapper.readline_w),
    write = interp2app(W_TextIOWrapper.write_w),
    seek = interp2app(W_TextIOWrapper.seek_w),
    detach = interp2app(W_TextIOWrapper.detach_w),
    flush = interp2app(W_TextIOWrapper.flush_w),
    close = interp2app(W_TextIOWrapper.close_w),

    line_buffering = interp_attrproperty("line_buffering", W_TextIOWrapper),
    readable = interp2app(W_TextIOWrapper.readable_w),
    writable = interp2app(W_TextIOWrapper.writable_w),
    seekable = interp2app(W_TextIOWrapper.seekable_w),
    fileno = interp2app(W_TextIOWrapper.fileno_w),
    )
