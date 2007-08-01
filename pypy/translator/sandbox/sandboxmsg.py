import sys, os
import struct
import select

from pypy.rpython.lltypesystem import rffi, lltype

# ____________________________________________________________
#
# Marshalling of external function calls' arguments
#

class MessageBuilder(object):
    def __init__(self):
        self.value = ['\xFF', '\xFF', '\xFF', '\xFF']

    def packstring(self, s):
        self.value.append("s")
        self._pack4(len(s))
        self.value += s
        return self

    def packccharp(self, p):
        length = 0
        while p[length] != '\x00':
            length += 1
        self.value.append("s")
        self._pack4(length)
        for i in range(length):
            self.value.append(p[i])
        return self

    def packbuf(self, buf, start, stop):
        self.value.append("s")
        self._pack4(stop - start)
        for i in range(start, stop):
            self.value.append(buf[i])
        return self

    def _pack4(self, n):
        self.value.append(chr((n >> 24) & 0xFF))
        self.value.append(chr((n >> 16) & 0xFF))
        self.value.append(chr((n >>  8) & 0xFF))
        self.value.append(chr((n      ) & 0xFF))

    def packnum(self, n):
        self.value.append("i")
        self._pack4(n)
        return self

    def packsize_t(self, n):
        self.value.append("I")
        self._pack4(rffi.cast(lltype.Signed, n))
        return self

    def _fixlength(self):
        n = len(self.value)
        self.value[0] = chr((n >> 24) & 0xFF)
        self.value[1] = chr((n >> 16) & 0xFF)
        self.value[2] = chr((n >>  8) & 0xFF)
        self.value[3] = chr((n      ) & 0xFF)

    def getvalue(self):
        self._fixlength()
        return ''.join(self.value)

    def as_rffi_buf(self):
        self._fixlength()
        value = self.value
        length = len(value)
        array = lltype.malloc(rffi.CCHARP.TO, length, flavor='raw')
        for i in range(length):
            array[i] = value[i]
        return array

    def getlength(self):
        return len(self.value)


class LLMessage(object):
    def __init__(self, value, start, stop):
        self.value = value
        assert 0 <= start <= stop
        self.pos = start
        self.stop = stop

    def _char(self):
        i = self.pos
        if i >= self.stop:
            raise ValueError
        self.pos = i + 1
        return self.value[i]

    def nextstring(self):
        t = self._char()
        if t != "s":
            raise ValueError
        length = self._next4()
        if length < 0:
            raise ValueError
        i = self.pos
        self.pos = i + length
        if self.pos > self.stop:
            raise ValueError
        # general version assuming that self.value is only indexable,
        # not sliceable.  See also the Message subclass.
        return ''.join([self.value[index] for index in range(i, self.pos)])

    def nextnum(self):
        t = self._char()
        if t != "i":
            raise ValueError
        return self._next4()

    def nextsize_t(self):
        t = self._char()
        if t != "I":
            raise ValueError
        return rffi.cast(rffi.SIZE_T, self._next4_unsigned())

    def _next4(self):
        c0 = ord(self._char())
        c1 = ord(self._char())
        c2 = ord(self._char())
        c3 = ord(self._char())
        if c0 >= 0x80:
            c0 -= 0x100
        return (c0 << 24) | (c1 << 16) | (c2 << 8) | c3

    def _next4_unsigned(self):
        c0 = ord(self._char())
        c1 = ord(self._char())
        c2 = ord(self._char())
        c3 = ord(self._char())
        return (c0 << 24) | (c1 << 16) | (c2 << 8) | c3

    def end(self):
        return self.pos >= self.stop


class Message(LLMessage):
    "NOT_RPYTHON"
    # 'value' is a regular string in this case,
    # allowing a more reasonable implementation of nextstring()
    def __init__(self, buf):
        LLMessage.__init__(self, buf, start=0, stop=len(buf))

    def nextstring(self):
        t = self._char()
        if t != "s":
            raise ValueError
        length = self._next4()
        i = self.pos
        self.pos = i + length
        if self.pos > self.stop:
            raise ValueError
        return self.value[i:self.pos]

    def decode(self, argtypes):
        "NOT_RPYTHON"  # optimized decoder
        v = self.value
        i = self.pos
        for t in argtypes:
            if v[i] != t:
                raise ValueError
            end = i + 5
            if t == "s":
                length, = struct.unpack("!i", v[i+1:i+5])
                end += length
                yield v[i+5:end]
            elif t == "i":
                result, = struct.unpack("!i", v[i+1:end])
                yield result
            elif t == "I":
                result, = struct.unpack("!I", v[i+1:end])
                yield result
            else:
                raise ValueError
            i = end
        if i != len(v):
            raise ValueError("more values to decode")

def encode_message(types, values):
    "NOT_RPYTHON"  # optimized encoder for messages
    chars = ["!"]
    entries = []
    if len(types) != len(values):
        raise ValueError("mismatch in the number of values to encode")
    for t, val in zip(types, values):
        chars.append("c")
        entries.append(t)
        if t == "s":
            if not isinstance(val, str):
                raise TypeError
            chars.append("i%ds" % len(val))
            entries.append(len(val))
            entries.append(val)
        elif t in "iI":
            chars.append(t)
            entries.append(val)
        else:
            raise ValueError
    data = struct.pack(''.join(chars), *entries)
    return struct.pack("!i", len(data) + 4) + data

def timeout_read(f, size, timeout=None):
    if size < 0:
        raise ValueError("negative size")
    if timeout is None:
        result = f.read(size)
    else:
        # XXX not Win32-compliant!
        assert not sys.platform.startswith('win'), "XXX fix me"
        # It also assumes that 'f' does no buffering!
        fd = f.fileno()
        result = ""
        while len(result) < size:
            iwtd, owtd, ewtd = select.select([fd], [], [], timeout)
            if not iwtd:
                raise Timeout("got %d bytes after %s seconds, expected %d" % (
                    len(result), timeout, size))
            buf = os.read(fd, size - len(result))
            if not buf:
                break
            result += buf
    if len(result) < size:
        raise EOFError
    return result

class Timeout(Exception):
    pass

def read_message(f, timeout=None):
    """NOT_RPYTHON - Warning! 'timeout' only works if 'f' is opened
    with no buffering at all!
    """
    msglength, = struct.unpack("!i", timeout_read(f, 4, timeout))
    buf = timeout_read(f, msglength - 4, timeout)
    return Message(buf)
