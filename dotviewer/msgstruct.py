import sys, os
from struct import pack, unpack, calcsize

MAGIC = -0x3b83728b

CMSG_INIT        = 'i'
CMSG_START_GRAPH = '['
CMSG_ADD_NODE    = 'n'
CMSG_ADD_EDGE    = 'e'
CMSG_ADD_LINK    = 'l'
CMSG_FIXED_FONT  = 'f'
CMSG_STOP_GRAPH  = ']'
CMSG_MISSING_LINK= 'm'
CMSG_SAY         = 's'

MSG_OK           = 'O'
MSG_ERROR        = 'E'
MSG_RELOAD       = 'R'
MSG_FOLLOW_LINK  = 'L'

# ____________________________________________________________

long_min = -2147483648
long_max = 2147483647


def message(tp, *values):
    #print >> sys.stderr, tp, values
    typecodes = ['']
    for v in values:
        if type(v) is str:
            typecodes.append('%ds' % len(v))
        elif 0 <= v < 256:
            typecodes.append('B')
        elif long_min <= v <= long_max:
            typecodes.append('l')
        else:
            typecodes.append('q')
    typecodes = ''.join(typecodes)
    if len(typecodes) < 256:
        return pack(("!B%dsc" % len(typecodes)) + typecodes,
                    len(typecodes), typecodes, tp, *values)
    else:
        # too many values - encapsulate the message in another one
        return message('\x00', typecodes, pack("!c" + typecodes, tp, *values))

def decodemessage(data):
    if data:
        limit = ord(data[0]) + 1
        if len(data) >= limit:
            typecodes = "!c" + data[1:limit]
            end = limit + calcsize(typecodes)
            if len(data) >= end:
                msg = unpack(typecodes, data[limit:end])
                if msg[0] == '\x00':
                    msg = unpack("!c" + msg[1], msg[2])
                return msg, data[end:]
            #elif end > 1000000:
            #    raise OverflowError
    return None, data

# ____________________________________________________________

class RemoteError(Exception):
    pass


class IO(object):
    _buffer = ''

    def sendmsg(self, tp, *values):
        self.sendall(message(tp, *values))

    def recvmsg(self):
        while True:
            msg, self._buffer = decodemessage(self._buffer)
            if msg is not None:
                break
            self._buffer += self.recv()
        if msg[0] != MSG_ERROR:
            return msg
        raise RemoteError(*msg[1:])


class FileIO(IO):
    def __init__(self, f_in, f_out):
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.setmode(f_in.fileno(), os.O_BINARY)
            msvcrt.setmode(f_out.fileno(), os.O_BINARY)
        self.f_in = f_in
        self.f_out = f_out

    def sendall(self, data):
        self.f_out.write(data)
        self.f_out.flush()

    def recv(self):
        fd = self.f_in.fileno()
        data = os.read(fd, 16384)
        if not data:
            raise EOFError
        return data

    def close_sending(self):
        self.f_out.close()

    def close(self):
        self.f_out.close()
        self.f_in.close()


class SocketIO(IO):
    def __init__(self, s):
        self.s = s

    def sendall(self, data):
        self.s.sendall(data)

    def recv(self):
        data = self.s.recv(16384)
        if not data:
            raise EOFError
        return data

    def close_sending(self):
        self.s.shutdown(1)    # SHUT_WR

    def close(self):
        self.s.close()
