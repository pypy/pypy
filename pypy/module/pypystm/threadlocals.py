"""
An STM-friendly subclass of OSThreadLocals.
"""

from pypy.module.thread.threadlocals import OSThreadLocals
from rpython.rlib import rstm


class STMThreadLocals(OSThreadLocals):
    threads_running = False
    _immutable_fields_ = ['threads_running?']

    def initialize(self, space):
        """NOT_RPYTHON: set up a mechanism to send to the C code the value
        set by space.actionflag.setcheckinterval()."""
        #
        def setcheckinterval_callback():
            self.configure_transaction_length(space)
        #
        assert space.actionflag.setcheckinterval_callback is None
        space.actionflag.setcheckinterval_callback = setcheckinterval_callback

    # XXX?
    #def getallvalues(self):
    #    raise ValueError

    def setup_threads(self, space):
        if not self.threads_running:
            # invalidate quasi-immutable if we have threads:
            self.threads_running = True

            # already done by rthread.ll_start_new_thread:
            # from rpython.rlib.objectmodel import invoke_around_extcall
            # self.configure_transaction_length(space)
            # invoke_around_extcall(rstm.before_external_call,
            #                       rstm.after_external_call,
            #                       rstm.enter_callback_call,
            #                       rstm.leave_callback_call)

    def configure_transaction_length(self, space):
        if self.threads_running:
            interval = space.actionflag.getcheckinterval()
            rstm.set_transaction_length(interval / 10000.0)

    def _set_ec(self, ec, register_in_valuedict=True):
        # must turn inevitable, for raw_thread_local.set(ec)
        rstm.become_inevitable()
        OSThreadLocals._set_ec(self, ec, register_in_valuedict)

    def leave_thread(self, space):
        # must turn inevitable, for raw_thread_local.set(None)
        rstm.become_inevitable()
        OSThreadLocals.leave_thread(self, space)
