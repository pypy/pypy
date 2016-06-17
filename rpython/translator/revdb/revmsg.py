import struct


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

    def __eq__(self, other):
        return (self.cmd == other.cmd and
                self.arg1 == other.arg1 and
                self.arg2 == other.arg2 and
                self.arg3 == other.arg3 and
                self.extra == other.extra)

    def __ne__(self, other):
        return not (self == other)


class ReplayProcess(object):
    def __init__(self, stdin, stdout):
        self.stdin = stdin
        self.stdout = stdout

    def send(self, msg):
        binary = struct.pack("iLqqq", msg.cmd, len(msg.extra),
                             msg.arg1, msg.arg2, msg.arg3)
        self.stdin.write(binary + msg.extra)

    def recv(self):
        binary = self.stdout.read(struct.calcsize("iLqqq"))
        cmd, size, arg1, arg2, arg3 = struct.unpack("iLqqq", binary)
        extra = self.stdout.read(size) if size > 0 else ""
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
