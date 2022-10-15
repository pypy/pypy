from .leakdetector import HPyDebugError, HPyLeakError, LeakDetector


def set_handle_stack_trace_limit(limit):
    from hpy.universal import _debug
    _debug.set_handle_stack_trace_limit(limit)


def disable_handle_stack_traces():
    from hpy.universal import _debug
    _debug.set_handle_stack_trace_limit(None)
