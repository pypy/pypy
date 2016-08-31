
INIT_VERSION_NUMBER = 0xd80100


# See the corresponding answers for details about messages.

CMD_FORK      = -1     # Message(CMD_FORK)
CMD_QUIT      = -2     # Message(CMD_QUIT)
CMD_FORWARD   = -3     # Message(CMD_FORWARD, steps, breakpoint_mode)
CMD_FUTUREIDS = -4     # Message(CMD_FUTUREIDS, extra=list-of-8bytes-uids)
CMD_PING      = -5     # Message(CMD_PING)
# extra commands which are not handled by revdb.c, but
# by revdb.register_debug_command()
CMD_PRINT       = 1    # Message(CMD_PRINT, extra=expression)
CMD_BACKTRACE   = 2    # Message(CMD_BACKTRACE)
CMD_LOCALS      = 3    # Message(CMD_LOCALS)
CMD_BREAKPOINTS = 4    # Message(CMD_BREAKPOINTS, stack_id,
                       #         extra="\0-separated names")
CMD_STACKID     = 5    # Message(CMD_STACKID, parent-flag)
CMD_ATTACHID    = 6    # Message(CMD_ATTACHID, small-num, unique-id)
CMD_COMPILEWATCH= 7    # Message(CMD_COMPILEWATCH, extra=expression)
CMD_CHECKWATCH  = 8    # Message(CMD_CHECKWATCH, extra=compiled_code)
CMD_WATCHVALUES = 9    # Message(CMD_WATCHVALUES, extra=texts)


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

# sent after an Attempted to do I/O or access raw memory, as the last message
ANSWER_ATTEMPT_IO = -25


# print one line of a file to the console, for CMD_PRINT
#    Message(ANSWER_LINECACHE, linenum, extra=filename)
ANSWER_LINECACHE  = 19

# print text to the console, for CMD_PRINT and others
#    Message(ANSWER_TEXT, extra=text)
ANSWER_TEXT       = 20

# CMD_STACKID returns the id of the current or parent frame (depending
# on the 'parent-flag' passed in), or 0 if not found.  The id can be just
# the stack depth, or it can be the unique id of the frame object.  When
# used in CMD_BREAKPOINTS, it means "break if we are entering/leaving a
# frame from/to the given frame".
#    Message(ANSWER_STACKID, stack-id)
ANSWER_STACKID    = 21

# sent from CMD_PRINT to record the existence of a recallable object
#    Message(ANSWER_NEXTNID, unique-id)
ANSWER_NEXTNID    = 22

# sent after CMD_COMPILEWATCH:
#    Message(ANSWER_WATCH, ok_flag, extra=marshalled_code)
# sent after CMD_CHECKWATCH:
#    Message(ANSWER_WATCH, ok_flag, extra=result_of_expr)
ANSWER_WATCH      = 23

# sent sometimes after CMD_BREAKPOINTS:
#    Message(ANSWER_CHBKPT, bkpt_num, extra=new_breakpoint_text)
ANSWER_CHBKPT     = 24


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
        cmd = self.cmd
        for key, value in globals().items():
            if (key.startswith('CMD_') or key.startswith('ANSWER_')) and (
                    value == cmd):
                cmd = key
                break
        return 'Message(%s, %d, %d, %d, %r)' % (cmd, self.arg1,
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
