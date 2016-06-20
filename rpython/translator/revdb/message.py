
INIT_VERSION_NUMBER = 0xd80100

CMD_FORK     = -1
CMD_QUIT     = -2
CMD_FORWARD  = -3
# extra commands which are not handled by revdb.c, but
# by revdb.register_debug_command()
CMD_PRINT       = 1
CMD_BACKTRACE   = 2
CMD_LOCALS      = 3
CMD_BREAKPOINTS = 4

ANSWER_INIT       = -20
ANSWER_STD        = -21
ANSWER_FORKED     = -22
ANSWER_AT_END     = -23
ANSWER_BREAKPOINT = -24

ANSWER_TEXT       = 20


class Message(object):
    """Represent messages sent and received to subprocesses
    started with --revdb-replay.
    """

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
