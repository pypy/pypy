
INIT_VERSION_NUMBER = 0xd80100


# See the corresponding answers for details about messages.

CMD_FORK     = -1      # Message(CMD_FORK)
CMD_QUIT     = -2      # Message(CMD_QUIT)
CMD_FORWARD  = -3      # Message(CMD_FORWARD, steps, breakpoint_mode)
# extra commands which are not handled by revdb.c, but
# by revdb.register_debug_command()
CMD_PRINT       = 1    # Message(CMD_PRINT, extra=expression)
CMD_BACKTRACE   = 2    # Message(CMD_BACKTRACE)
CMD_LOCALS      = 3    # Message(CMD_LOCALS)
CMD_BREAKPOINTS = 4    # Message(CMD_BREAKPOINTS, extra="\0-separated names")



# the first message sent by the first child:
#    Message(ANSWER_INIT, INIT_VERSION_NUMBER, total_stop_points)
ANSWER_INIT       = -20

# sent when the child is done and waiting for the next command:
#    Message(ANSWER_READY, current_time, currently_created_objects)
ANSWER_READY      = -21

# sent after CMD_FORK:
#    Message(ANSWER_FORKED, child_pid)
ANSWER_FORKED     = -22

# sent when a child reaches the end (should not occur with process.py)
#    Message(ANSWER_AT_END)           (the child exits afterwards)
ANSWER_AT_END     = -23

# breakpoint detected in CMD_FORWARD:
#    Message(ANSWER_BREAKPOINT, break_time, break_created_objects, bpkt_num)
# if breakpoint_mode=='b': sent immediately when seeing a breakpoint,
#                          followed by ANSWER_STD with the same time
# if breakpoint_mode=='r': sent when we're done going forward, about
#                          the most recently seen breakpoint
# if breakpoint_mode=='i': ignored, never sent
ANSWER_BREAKPOINT = -24

# print text to the console, for CMD_PRINT and others
#    Message(ANSWER_TEXT, extra=text)
ANSWER_TEXT       = 20


# ____________________________________________________________


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
