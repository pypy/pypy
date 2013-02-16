from pypy.interpreter.executioncontext import AbstractActionFlag
from rpython.rlib import jit
from rpython.rlib.rsignal import pypysig_getaddr_occurred


class SignalActionFlag(AbstractActionFlag):
    # This class uses the C-level pypysig_counter variable as the tick
    # counter.  The C-level signal handler will reset it to -1 whenever
    # a signal is received.  This causes CheckSignalAction.perform() to
    # be called.

    def get_ticker(self):
        p = pypysig_getaddr_occurred()
        return p.c_value

    def reset_ticker(self, value):
        p = pypysig_getaddr_occurred()
        p.c_value = value

    def rearm_ticker(self):
        p = pypysig_getaddr_occurred()
        p.c_value = -1

    def decrement_ticker(self, by):
        p = pypysig_getaddr_occurred()
        value = p.c_value
        if self.has_bytecode_counter:    # this 'if' is constant-folded
            if jit.isconstant(by) and by == 0:
                pass     # normally constant-folded too
            else:
                value -= by
                p.c_value = value
        return value
