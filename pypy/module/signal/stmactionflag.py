from pypy.interpreter.executioncontext import AbstractActionFlag
from rpython.rlib import jit
from rpython.rlib.rsignal import pypysig_get_occurred, pypysig_set_occurred


class SignalActionFlag(AbstractActionFlag):
    # This is mostly a copy of actionflag.py, but written in a way
    # that doesn't force atomic transactions --- but isn't very JIT
    # friendly yet.

    def get_ticker(self):
        return pypysig_get_occurred()

    def reset_ticker(self, value):
        pypysig_set_occurred(value)

    def rearm_ticker(self):
        pypysig_set_occurred(-1)

    def decrement_ticker(self, by):
        value = pypysig_get_occurred()
        if self.has_bytecode_counter:    # this 'if' is constant-folded
            if jit.isconstant(by) and by == 0:
                pass     # normally constant-folded too
            else:
                value -= by
                pypysig_set_occurred(value)
        return value
