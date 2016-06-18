import os, struct, socket, errno
from rpython.translator.revdb import ancillary


INIT_VERSION_NUMBER   = 0xd80100

CMD_FORK     = -1
CMD_QUIT     = -2
CMD_FORWARD  = -3

ANSWER_INIT    = -20
ANSWER_STD     = -21
ANSWER_FORKED  = -22
ANSWER_AT_END  = -23


class Message(object):
    def __init__(self, cmd, arg1=0, arg2=0, arg3=0, extra=""):
        self.cmd = cmd
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.extra = extra

    def __repr__(self):
        return 'Message(%d, %d, %d, %d, %r)' % (self.cmd, self.arg1,
                                                self.arg2, self.arg3,
                                                self.extra)

    def __eq__(self, other):
        return (self.cmd == other.cmd and
                self.arg1 == other.arg1 and
                self.arg2 == other.arg2 and
                self.arg3 == other.arg3 and
                self.extra == other.extra)

    def __ne__(self, other):
        return not (self == other)


class ReplayProcess(object):
    def __init__(self, pid, control_socket):
        self.pid = pid
        self.control_socket = control_socket

    def _recv_all(self, size):
        pieces = []
        while size > 0:
            data = self.control_socket.recv(size)
            if not data:
                raise EOFError
            size -= len(data)
            pieces.append(data)
        return ''.join(pieces)

    def send(self, msg):
        binary = struct.pack("iIqqq", msg.cmd, len(msg.extra),
                             msg.arg1, msg.arg2, msg.arg3)
        self.control_socket.sendall(binary + msg.extra)

    def recv(self):
        binary = self._recv_all(struct.calcsize("iIqqq"))
        cmd, size, arg1, arg2, arg3 = struct.unpack("iIqqq", binary)
        extra = self._recv_all(size)
        return Message(cmd, arg1, arg2, arg3, extra)

    def expect(self, cmd, arg1=0, arg2=0, arg3=0, extra=""):
        msg = self.recv()
        assert msg.cmd == cmd
        if arg1 is not Ellipsis:
            assert msg.arg1 == arg1
        if arg2 is not Ellipsis:
            assert msg.arg2 == arg2
        if arg3 is not Ellipsis:
            assert msg.arg3 == arg3
        if extra is not Ellipsis:
            assert msg.extra == extra
        return msg

    def fork(self):
        self.send(Message(CMD_FORK))
        s1, s2 = socket.socketpair()
        ancillary.send_fds(self.control_socket.fileno(), [s2.fileno()])
        s2.close()
        msg = self.expect(ANSWER_FORKED, Ellipsis)
        child_pid = msg.arg1
        return ReplayProcess(child_pid, s1)

    def close(self):
        self.send(Message(CMD_QUIT))

    def forward(self, steps):
        self.send(Message(CMD_FORWARD, steps))
        return self.expect(ANSWER_STD, Ellipsis, Ellipsis)

    def current_time(self):
        return self.forward(0).arg1

    def currently_created_objects(self):
        return self.forward(0).arg2
