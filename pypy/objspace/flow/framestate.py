from pypy.interpreter.pyframe import PyFrame
from pypy.objspace.flow.model import *

class FrameState:
    # XXX this class depends on the internal state of PyFrame objects

    def __init__(self, state):
        if isinstance(state, PyFrame):
            self.mergeable = state.getfastscope() + state.valuestack.items
            self.nonmergeable = (
                state.blockstack.items[:],
                state.last_exception,
                state.next_instr,
            )
        elif isinstance(state, tuple):
            self.mergeable, self.nonmergeable = state
        else:
            raise TypeError("can't get framestate for %r" % 
                            state.__class__.__name__)

    def restoreframe(self, frame):
        if isinstance(frame, PyFrame):
            fastlocals = len(frame.fastlocals_w)
            frame.setfastscope(self.mergeable[:fastlocals])
            frame.valuestack.items[:] = self.mergeable[fastlocals:]
            (
                frame.blockstack.items[:],
                frame.last_exception,
                frame.next_instr,
            ) = self.nonmergeable
        else:
            raise TypeError("can't set framestate for %r" % 
                            frame.__class__.__name__)

    def copy(self):
        "Make a copy of this state in which all Variables are fresh."
        newstate = []
        for w in self.mergeable:
            if isinstance(w, Variable):
                w = Variable()
            newstate.append(w)
        return FrameState((newstate, self.nonmergeable))

    def getvariables(self):
        return [w for w in self.mergeable if isinstance(w, Variable)]

    def __eq__(self, other):
        """Two states are equal
        if they only use different Variables at the same place"""
        # safety check, don't try to compare states with different
        # nonmergeable states
        assert isinstance(other, FrameState)
        assert len(self.mergeable) == len(other.mergeable)
        assert self.nonmergeable == other.nonmergeable
        for w1, w2 in zip(self.mergeable, other.mergeable):
            if not (w1 == w2 or (isinstance(w1, Variable) and
                                 isinstance(w2, Variable))):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def union(self, other):
        """Compute a state that is at least as general as both self and other.
           A state 'a' is more general than a state 'b' if all Variables in 'b'
           are also Variables in 'a', but 'a' may have more Variables.
        """
        newstate = []
        for w1, w2 in zip(self.mergeable, other.mergeable):
            if isinstance(w1, Variable):
                w = Variable()  # new fresh Variable
            elif isinstance(w1, Constant):
                if w1 == w2:
                    w = w1
                else:
                    w = Variable()  # generalize different constants
            else:
                raise TypeError('union of %r and %r' % (w1.__class__.__name__,
                                                        w2.__class__.__name__))
            newstate.append(w)
        return FrameState((newstate, self.nonmergeable))

    def getoutputargs(self, targetstate):
        "Return the output arguments needed to link self to targetstate."
        result = []
        for w_output, w_target in zip(self.mergeable, targetstate.mergeable):
            if isinstance(w_target, Variable):
                result.append(w_output)
            elif not isinstance(w_target, Constant):
                raise TypeError('output arg %r' % w_target.__class__.__name__)
        return result

