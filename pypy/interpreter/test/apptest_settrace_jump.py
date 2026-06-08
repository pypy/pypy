"""Apptests for f_lineno jump validation (sys.settrace frame jumping).

Mirrors the lib-python JumpTestCase structure: functions defined at module
level, JumpTracer with decorated=True, so firstLine is set dynamically.
"""
import sys
import re


class JumpTracer:
    def __init__(self, function, jumpFrom, jumpTo, event='line', decorated=False):
        self.code = function.__code__
        self.jumpFrom = jumpFrom
        self.jumpTo = jumpTo
        self.event = event
        self.firstLine = None if decorated else self.code.co_firstlineno
        self.done = False

    def trace(self, frame, event, arg):
        if self.done:
            return
        if (self.firstLine is None and frame.f_code == self.code and event == 'line'):
            self.firstLine = frame.f_lineno - 1
        if (event == self.event and self.firstLine is not None and
                frame.f_lineno == self.firstLine + self.jumpFrom):
            f = frame
            while f is not None and f.f_code != self.code:
                f = f.f_back
            if f is not None:
                try:
                    frame.f_lineno = self.firstLine + self.jumpTo
                except TypeError:
                    frame.f_lineno = self.jumpTo
                self.done = True
        return self.trace


def run_jump_test(func, jumpFrom, jumpTo, expected, error=None, decorated=False):
    wrapped = func
    while hasattr(wrapped, '__wrapped__'):
        wrapped = wrapped.__wrapped__

    tracer = JumpTracer(wrapped, jumpFrom, jumpTo, decorated=decorated)
    sys.settrace(tracer.trace)
    output = []
    exc_raised = None
    try:
        if error is None:
            func(output)
        else:
            try:
                func(output)
            except error[0] as e:
                exc_raised = str(e)
            else:
                raise AssertionError("expected %s, got no exception" % error[0])
    finally:
        sys.settrace(None)

    if error is not None:
        exc_type, pattern = error
        if not re.search(pattern, exc_raised):
            raise AssertionError(
                "expected %s matching %r, got: %r" % (exc_type.__name__, pattern, exc_raised))

    if output != expected:
        raise AssertionError("output mismatch: expected %r, got %r" % (expected, output))


# ---- test functions at module level (matching lib-python structure) ----

def _no_jump_over_return_try_finally_in_finally_block(output):
    try:
        output.append(2)
    finally:
        output.append(4)
        output.append(5)
        return
        try:
            output.append(8)
        finally:
            output.append(10)
        pass
    output.append(12)


def test_no_jump_over_return_try_finally_in_finally_block():
    run_jump_test(
        _no_jump_over_return_try_finally_in_finally_block,
        jumpFrom=5, jumpTo=11,
        expected=[2, 4],
        error=(ValueError, 'exception'),
        decorated=True,
    )
