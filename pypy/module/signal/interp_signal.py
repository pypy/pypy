from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.miscutils import Action
from pypy.module.signal import ctypes_signal


class CheckSignalAction(Action):
    """A repeatitive action at the space level, checking if the
    signal_occurred flag is set and if so, scheduling ReportSignal actions.
    """
    repeat = True

    def __init__(self, space):
        self.space = space

    def perform(self):
        if flag_queue.signal_occurred:
            flag_queue.signal_occurred = 0
            node = flag_queue.head
            signum = 0
            while node is not None:
                if node.flag:
                    node.flag = 0
                    main_ec = self.space.threadlocals.getmainthreadvalue()
                    main_ec.add_pending_action(ReportSignal(self.space,
                                                            node, signum))
                node = node.next
                signum += 1


class ReportSignal(Action):
    """A one-shot action for the main thread's execution context."""

    def __init__(self, space, node, signum):
        self.space = space
        self.node = node
        self.signum = signum

    def perform(self):
        w_handler = self.node.w_handler
        if w_handler is not None:
            space = self.space
            ec = space.getexecutioncontext()
            try:
                w_frame = ec.framestack.top()
            except IndexError:
                w_frame = space.w_None
            space.call_function(w_handler, space.wrap(self.signum), w_frame)


# ____________________________________________________________
# Global flags set by the signal handler

# XXX some of these data structures may need to
#     use the "volatile" keyword in the generated C code

class FlagQueueNode(object):
    def __init__(self):
        self.flag = 0
        self.next = None
        self.w_handler = None

class FlagQueue(object):
    signal_occurred = 0
    head = FlagQueueNode()

flag_queue = FlagQueue()

def get_flag_queue_signum(signum):
    node = flag_queue.head
    while signum > 0:
        if node.next is None:
            node.next = FlagQueueNode()
        node = node.next
        signum -= 1
    return node

def generic_signal_handler(signum):
    node = flag_queue.head
    index = 0
    while index < signum:
        node = node.next
        index += 1
    node.flag = 1
    flag_queue.signal_occurred = 1
    # XXX may need to set the handler again, in case the OS clears it

def os_setsig(signum, handler):
    return ctypes_signal.signal(signum, handler)

# ____________________________________________________________

def signal(space, signum, w_handler):
    ec      = space.getexecutioncontext()
    main_ec = space.threadlocals.getmainthreadvalue()
    if ec is not main_ec:
        raise OperationError(space.w_ValueError,
                             space.wrap("signal() must be called from the "
                                        "main thread"))
    node = get_flag_queue_signum(signum)
    node.w_handler = w_handler
    # XXX special values SIG_IGN, SIG_DFL
    handler = ctypes_signal.sighandler_t(generic_signal_handler)
    os_setsig(signum, handler)
    # XXX return value
signal.unwrap_spec = [ObjSpace, int, W_Root]
