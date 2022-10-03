from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal.llapi import cts

@API.func("void HPy_ReenterPythonExecution(HPyContext *ctx, HPyThreadState state)",
    gil="acquire",
)
def HPy_ReenterPythonExecution(space, handles, ctx, state):
    """Acquire the global interpreter lock (if it has been created) and set the
    thread state to tstate, which must not be NULL.  If the lock has been
    created, the current thread must not have acquired it, otherwise deadlock
    ensues."""
    #for now...
    pass

@API.func("HPyThreadState HPy_LeavePythonExecution(HPyContext *ctx)",
    error_value=cts.cast("HPyThreadState", -1),
    gil="release",
)
def HPy_LeavePythonExecution(space, handles, ctx):
    """Release the global interpreter lock (if it has been created)
    and reset the thread state to NULL, returning the
    previous thread state.  If the lock has been created,
    the current thread must have acquired it."""
    # for now
    return cts.cast("HPyThreadState", 0)
