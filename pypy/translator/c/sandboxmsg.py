import sys, os
import struct
import select

from pypy.annotation import policy, model as annmodel

# ____________________________________________________________
#
# Marshalling of external function calls' arguments
#

class MessageBuilder(object):
    def __init__(self):
        self.value = ['\xFF', '\xFF', '\xFF', '\xFF']

    def packstring(self, s):
        self.packnum(len(s), "s")
        self.value += s
        return self
    packstring._annenforceargs_ = policy.Sig(None, str)

    def packccharp(self, p):
        length = 0
        while p[length] != '\x00':
            length += 1
        self.packnum(length, "s")
        for i in range(length):
            self.value.append(p[i])
        return self

    def packnum(self, n, prefix="i"):
        self.value.append(prefix)
        self.value.append(chr((n >> 24) & 0xFF))
        self.value.append(chr((n >> 16) & 0xFF))
        self.value.append(chr((n >>  8) & 0xFF))
        self.value.append(chr((n      ) & 0xFF))
        return self
    packnum._annenforceargs_ = policy.Sig(None, int, annmodel.SomeChar())

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
        from pypy.rpython.lltypesystem import lltype, rffi
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
        self.pos = start
        self.stop = stop

    def _char(self):
        i = self.pos
        if i >= self.stop:
            raise ValueError
        self.pos = i + 1
        return self.value[i]

    def nextstring(self):
        length = self.nextnum("s")
        i = self.pos
        self.pos = i + length
        if self.pos > self.stop:
            raise ValueError
        # general version assuming that self.value is only indexable,
        # not sliceable.  See also the Message subclass.
        return ''.join([self.value[index] for index in range(i, self.pos)])

    def nextnum(self, prefix="i"):
        t = self._char()
        if t != prefix:
            raise ValueError
        c0 = ord(self._char())
        c1 = ord(self._char())
        c2 = ord(self._char())
        c3 = ord(self._char())
        if c0 >= 0x80:
            c0 -= 0x100
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
        length = self.nextnum("s")
        i = self.pos
        self.pos = i + length
        if self.pos > self.stop:
            raise ValueError
        return self.value[i:self.pos]

def timeout_read(f, size, timeout=None):
    if size < 0:
        raise ValueError("negative size")
    if timeout is None:
        return f.read(size)
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
                raise EOFError
            result += buf
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
