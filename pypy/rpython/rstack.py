"""
This file defines utilities for manipulating the stack in an
RPython-compliant way, intended mostly for use by the Stackless PyPy.
"""

import inspect

def stack_unwind():
    raise RuntimeError("cannot unwind stack in non-translated versions")

def stack_frames_depth():
    return len(inspect.stack())

def stack_too_big():
    return False

def stack_check():
    if stack_too_big():
        # stack_unwind implementation is different depending on if stackless
        # is enabled. If it is it unwinds the stack, otherwise it simply
        # raises a RuntimeError.
        stack_unwind()

# ____________________________________________________________

def yield_current_frame_to_caller():
    raise NotImplementedError("only works in translated versions")

class frame_stack_top(object):
    def switch(self):
        raise NotImplementedError("only works in translated versions")
    def clone(self):
        raise NotImplementedError("only works in translated versions")
