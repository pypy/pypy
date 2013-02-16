from pypy.interpreter.executioncontext import AbstractActionFlag
from rpython.rlib import jit, rstm
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rsignal import pypysig_get_occurred, pypysig_set_occurred


class SignalActionFlag(AbstractActionFlag):
    # This is mostly a copy of actionflag.py, but written in a way
    # that doesn't force atomic transactions --- but isn't very JIT
    # friendly yet.

    def get_ticker(self):
        if we_are_translated():
            return pypysig_get_occurred()
        else:
            return 42

    def reset_ticker(self, value):
        if we_are_translated():
            # explicit manipulation of the counter needs to turn the
            # transaction inevitable.  We don't turn it inevitable in
            # decrement_ticker() or if a real signal is received, but
            # we turn it inevitable when this condition is detected
            # and we reset a value >= 0.
            rstm.become_inevitable()
            pypysig_set_occurred(value)

    def rearm_ticker(self):
        if we_are_translated():
            pypysig_set_occurred(-1)

    def decrement_ticker(self, by):
        if we_are_translated():
            value = pypysig_get_occurred()
            if self.has_bytecode_counter:    # this 'if' is constant-folded
                if jit.isconstant(by) and by == 0:
                    pass     # normally constant-folded too
                else:
                    value -= by
                    pypysig_set_occurred(value)
            return value
        else:
            return 42
