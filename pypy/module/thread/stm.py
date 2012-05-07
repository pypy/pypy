"""
Software Transactional Memory emulation of the GIL.
"""

from pypy.module.thread.threadlocals import OSThreadLocals
from pypy.rlib import rstm
from pypy.rlib.objectmodel import invoke_around_extcall


class STMThreadLocals(OSThreadLocals):

    def initialize(self, space):
        pass

    def setup_threads(self, space):
        invoke_around_extcall(rstm.before_external_call,
                              rstm.after_external_call,
                              rstm.enter_callback_call,
                              rstm.leave_callback_call)

    def reinit_threads(self, space):
        self.setup_threads(space)
