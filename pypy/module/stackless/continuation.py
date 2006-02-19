"""
This module exposes primitive continuations both to
interpreter and application level.

The reason is to make testing of higher level strutures
easier to test on top of compiled pypy.

This is an implementation of one-shot implementations.
Some time earlier, I was against this naming. Sorry
about that -- I now think it is appropriate.

"""
from pypy.rpython.rstack import yield_current_frame_to_caller

import sys, os

class ContinuationError(SystemError):
    pass

class ContinuationStart(Exception):
    pass

def output(stuff):
    os.write(2, '-- ' + stuff + '\n')

class Continuation(object):
    def __init__(self, frame):
        if frame is None:
            os.write(2, "+++ __init__ called with Null frame: %x\n" % id(self))
            raise ContinuationError
        output("new continuation self=%x frame=%x" % (id(self), id(frame)))
        self.frame = frame

    def switch(self):
        if self.frame is None:
            os.write(2, "+++ tried to shoot a continuation twice: %x\n" % id(self))
            raise ContinuationError
        frame, self.frame = self.frame, None
        output("switch to self=%x frame=%x" % (id(self), id(frame)))
        frame = frame.switch()
        output("after switch self=%x frame=%x" % (id(self), id(frame)))
        if frame is None:
            output('returning exhausted continuation %x' % id(self))
            return self
        return Continuation(frame)

    def capture():
        output('capture is calling _bind')
        frame = Continuation._bind()
        self = Continuation(frame)
        output("capture returning with self=%x frame=%x" % (id(self), id(frame)))
        return self
    capture = staticmethod(capture)

    def _bind():
        output('_bind will yield the current frame now')
        frame = yield_current_frame_to_caller()
        output('_bind after yield, with frame=%x' % id(frame))
        #if id(frame) != 1:
         #   raise ContinuationStart, Continuation(frame)
        return frame # return twice
    _bind = staticmethod(_bind)

    def __del__(self):
        
        """
        Dropping a continuation is a fatal error.
        """
        if self.frame is not None:
            os.write(2, "+++ an active continuation was dropped: %x\n" % id(self))
            raise ContinuationError
