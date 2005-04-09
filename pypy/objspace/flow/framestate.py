from pypy.interpreter.pyframe import PyFrame, ControlFlowException
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import instantiate
from pypy.objspace.flow.model import *

class FrameState:
    # XXX this class depends on the internal state of PyFrame objects

    def __init__(self, state):
        if isinstance(state, PyFrame):
            data = []
            for w in state.getfastscope():
                if w is None:
                    data.append(Constant(undefined_value))
                else:
                    data.append(w)
            data.extend(state.valuestack.items)
            if state.last_exception is None:
                data.append(Constant(None))
                data.append(Constant(None))
            else:
                data.append(state.last_exception.w_type)
                data.append(state.last_exception.w_value)
            recursively_flatten(state.space, data)
            self.mergeable = data
            self.nonmergeable = (
                state.blockstack.items[:],
                state.next_instr,
                state.w_locals,
            )
        elif isinstance(state, tuple):
            self.mergeable, self.nonmergeable = state
        else:
            raise TypeError("can't get framestate for %r" % 
                            state.__class__.__name__)
        self.next_instr = self.nonmergeable[1]
        for w1 in self.mergeable:
            assert isinstance(w1, (Variable, Constant)), (
                '%r found in frame state' % w1)

    def restoreframe(self, frame):
        if isinstance(frame, PyFrame):
            fastlocals = len(frame.fastlocals_w)
            data = self.mergeable[:]
            recursively_unflatten(frame.space, data)
            fastscope = []
            for w in data[:fastlocals]:
                if isinstance(w, Constant) and w.value is undefined_value:
                    fastscope.append(None)
                else:
                    fastscope.append(w)
            frame.setfastscope(fastscope)
            frame.valuestack.items[:] = data[fastlocals:-2]
            if data[-2] == Constant(None):
                assert data[-1] == Constant(None)
                frame.last_exception = None
            else:
                frame.last_exception = OperationError(data[-2], data[-1])
            (
                frame.blockstack.items[:],
                frame.next_instr,
                frame.w_locals,
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
        try:
            for w1, w2 in zip(self.mergeable, other.mergeable):
                newstate.append(union(w1, w2))
        except UnionError:
            return None
        return FrameState((newstate, self.nonmergeable))

    def getoutputargs(self, targetstate):
        "Return the output arguments needed to link self to targetstate."
        result = []
        for w_output, w_target in zip(self.mergeable, targetstate.mergeable):
            if isinstance(w_target, Variable):
                result.append(w_output)
        return result


class UnionError(Exception):
    "The two states should be merged."

def union(w1, w2):
    "Union of two variables or constants."
    if isinstance(w1, Variable) or isinstance(w2, Variable):
        return Variable()  # new fresh Variable
    if isinstance(w1, Constant) and isinstance(w2, Constant):
        if w1 == w2:
            return w1
        # ControlFlowException represent stack unrollers in the stack.
        # They should not be merged because they will be unwrapped.
        # This is needed for try:except: and try:finally:, though
        # it makes the control flow a bit larger by duplicating the
        # handlers.
        dont_merge_w1 = w1 in UNPICKLE_TAGS or isinstance(w1.value, SpecTag)
        dont_merge_w2 = w2 in UNPICKLE_TAGS or isinstance(w2.value, SpecTag)
        if dont_merge_w1 or dont_merge_w2:
            raise UnionError
        else:
            return Variable()  # generalize different constants
    raise TypeError('union of %r and %r' % (w1.__class__.__name__,
                                            w2.__class__.__name__))

# ____________________________________________________________
#
# Support for explicit specialization: in code using global constants
# that are instances of SpecTag, code paths are not merged when
# the same variable holds a different SpecTag instance.

class SpecTag(object):
    def __repr__(self):
        return 'SpecTag(%d)' % id(self)
    def _freeze_(self):
        return True

# ____________________________________________________________
#
# We have to flatten out the state of the frame into a list of
# Variables and Constants.  This is done above by collecting the
# locals and the items on the value stack, but the latter may contain
# ControlFlowExceptions.  We have to handle these specially, because
# some of them hide references to more Variables and Constants.
# The trick is to flatten ("pickle") them into the list so that the
# extra Variables show up directly in the list too.

class PickleTag:
    pass

PICKLE_TAGS = {}
UNPICKLE_TAGS = {}

def recursively_flatten(space, lst):
    i = 0
    while i < len(lst):
        item = lst[i]
        if not (isinstance(item, Constant) and
                isinstance(item.value, ControlFlowException)):
            i += 1
        else:
            unroller = item.value
            vars = unroller.state_unpack_variables(space)
            key = unroller.__class__, len(vars)
            try:
                tag = PICKLE_TAGS[key]
            except:
                tag = PICKLE_TAGS[key] = Constant(PickleTag())
                UNPICKLE_TAGS[tag] = key
            lst[i:i+1] = [tag] + vars

def recursively_unflatten(space, lst):
    for i in range(len(lst)-1, -1, -1):
        item = lst[i]
        if item in UNPICKLE_TAGS:
            unrollerclass, argcount = UNPICKLE_TAGS[item]
            arguments = lst[i+1: i+1+argcount]
            del lst[i+1: i+1+argcount]
            unroller = instantiate(unrollerclass)
            unroller.state_pack_variables(space, *arguments)
            lst[i] = Constant(unroller)
