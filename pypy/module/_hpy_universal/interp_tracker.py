from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.objectmodel import newlist_hint
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles

class W_Tracker(W_Root):
    def __init__(self, size):
        self.handles = newlist_hint(size)

    def add(self, h):
        self.handles.append(h)

    def forget_all(self):
        self.handles = []

    def close(self, space):
        for h in self.handles:
            state.handles.close(h)

@API.func("HPyTracker HPyTracker_New(HPyContext ctx, HPy_ssize_t size)", error_value=0)
def HPyTracker_New(space, state, ctx, size):
    w_tracker = W_Tracker(size)
    return state.handles.new(w_tracker)

@API.func("int HPyTracker_Add(HPyContext ctx, HPyTracker ht, HPy h)",
          error_value=API.int(-1))
def HPyTracker_Add(space, state, ctx, ht, h):
    w_tracker = state.handles.deref(ht)
    assert isinstance(w_tracker, W_Tracker)
    w_tracker.add(h)
    return API.int(0)

@API.func("void HPyTracker_ForgetAll(HPyContext ctx, HPyTracker ht)")
def HPyTracker_ForgetAll(space, state, ctx, ht):
    w_tracker = state.handles.deref(ht)
    assert isinstance(w_tracker, W_Tracker)
    w_tracker.forget_all()

@API.func("void HPyTracker_Close(HPyContext ctx, HPyTracker ht)")
def HPyTracker_Close(space, state, ctx, ht):
    w_tracker = state.handles.deref(ht)
    assert isinstance(w_tracker, W_Tracker)
    w_tracker.close(space)
    state.handles.close(ht)
