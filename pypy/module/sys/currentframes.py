"""
Implementation of the 'sys._current_frames()' routine.
"""
from pypy.interpreter import gateway

app = gateway.applevel('''
"NOT_RPYTHON"
import __builtin__

class fake_code(object):
    co_name = "?"
    co_filename = "?"
    co_firstlineno = 0

class fake_frame(object):
    f_back = None
    f_builtins = __builtin__.__dict__
    f_code = fake_code()
    f_exc_traceback = None
    f_exc_type = None
    f_exc_value = None
    f_globals = {}
    f_lasti = -1
    f_lineno = 0
    f_locals = {}
    f_restricted = False
    f_trace = None

    def __init__(self, f):
        if f is not None:
            for name in ["f_builtins", "f_code", "f_globals", "f_lasti",
                         "f_lineno"]:
                setattr(self, name, getattr(f, name))
''')

def _current_frames(space):
    """_current_frames() -> dictionary

    Return a dictionary mapping each current thread T's thread id to T's
    current stack "frame".  Functions in the traceback module can build the
    call stack given such a frame.

    Note that in PyPy this returns fake frame objects, to avoid a runtime
    penalty everywhere with the JIT.  (So far these fake frames can be
    completely uninformative depending on the JIT state; we could return
    more with more efforts.)

    This function should be used for specialized purposes only."""
    w_result = space.newdict()
    w_fake_frame = app.wget(space, "fake_frame")
    w_fake_code  = app.wget(space, "fake_code")
    ecs = space.threadlocals.getallvalues()
    for thread_ident, ec in ecs.items():
        vref = ec.topframeref
        frames = []
        while not vref.virtual:
            f = vref()
            if f is None:
                break
            frames.append(f)
            vref = f.f_backref
        else:
            frames.append(None)
        #
        w_topframe = space.wrap(None)
        w_prevframe = None
        for f in frames:
            w_nextframe = space.call_function(w_fake_frame, space.wrap(f))
            if w_prevframe is None:
                w_topframe = w_nextframe
            else:
                space.setattr(w_prevframe, space.wrap('f_back'), w_nextframe)
            w_prevframe = w_nextframe
        #
        space.setitem(w_result,
                      space.wrap(thread_ident),
                      w_topframe)
    return w_result
