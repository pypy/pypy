import pytest

class tracecontext:
    """Contex manager that traces its enter and exit."""
    def __init__(self, output, value):
        self.output = output
        self.value = value

    def __enter__(self):
        self.output.append(self.value)

    def __exit__(self, *exc_info):
        self.output.append(-self.value)

class JumpTracer:
    def __init__(self, function, jumpFrom, jumpTo, event='line',
                 decorated=False):
        self.code = function.func_code
        self.jumpFrom = jumpFrom
        self.jumpTo = jumpTo
        self.event = event
        self.firstLine = None if decorated else self.code.co_firstlineno
        self.done = False

    def trace(self, frame, event, arg):
        if self.done:
            return
        # frame.f_code.co_firstlineno is the first line of the decorator when
        # 'function' is decorated and the decorator may be written using
        # multiple physical lines when it is too long. Use the first line
        # trace event in 'function' to find the first line of 'function'.
        if (self.firstLine is None and frame.f_code == self.code and
                event == 'line'):
            self.firstLine = frame.f_lineno - 1
        if (event == self.event and self.firstLine and
                frame.f_lineno == self.firstLine + self.jumpFrom):
            f = frame
            while f is not None and f.f_code != self.code:
                f = f.f_back
            if f is not None:
                # Cope with non-integer self.jumpTo (because of
                # no_jump_to_non_integers below).
                try:
                    frame.f_lineno = self.firstLine + self.jumpTo
                except TypeError:
                    frame.f_lineno = self.jumpTo
                self.done = True
        return self.trace


def run_test(func, jumpFrom, jumpTo, expected, error=None,
             event='line', decorated=False):
    import sys
    tracer = JumpTracer(func, jumpFrom, jumpTo, event, decorated)
    sys.settrace(tracer.trace)
    try:
        output = []
        if error is None:
            func(output)
        else:
            with pytest.raises(error[0]) as exc_info:
                func(output)
            assert error[1] in str(exc_info.value.args[0])
    finally:
        sys.settrace(None)
    assert expected == output

def jump_test(jumpFrom, jumpTo, expected, error=None, event='line'):
    """Decorator that creates a test that makes a jump
    from one place to another in the following code.
    """
    def decorator(func):
        #@wraps(func)
        def test():
            run_test(func, jumpFrom, jumpTo, expected,
                     error=error, event=event, decorated=True)
        return test
    return decorator

## The first set of 'jump' tests are for things that are allowed:
@jump_test(1, 3, [3])
def test_jump_simple_forwards(output):
    output.append(1)
    output.append(2)
    output.append(3)

@jump_test(2, 1, [1, 1, 2])
def test_jump_simple_backwards(output):
    output.append(1)
    output.append(2)

@jump_test(3, 5, [2, 5])
def test_jump_out_of_block_forwards(output):
    for i in 1, 2:
        output.append(2)
        for j in [3]:  # Also tests jumping over a block
            output.append(4)
    output.append(5)

@jump_test(6, 1, [1, 3, 5, 1, 3, 5, 6, 7])
def test_jump_out_of_block_backwards(output):
    output.append(1)
    for i in [1]:
        output.append(3)
        for j in [2]:  # Also tests jumping over a block
            output.append(5)
        output.append(6)
    output.append(7)

@jump_test(1, 2, [3])
def test_jump_to_codeless_line(output):
    output.append(1)
    # Jumping to this line should skip to the next one.
    output.append(3)

@jump_test(2, 2, [1, 2, 3])
def test_jump_to_same_line(output):
    output.append(1)
    output.append(2)
    output.append(3)

# Tests jumping within a finally block, and over one.
@jump_test(4, 9, [2, 9])
def test_jump_in_nested_finally(output):
    try:
        output.append(2)
    finally:
        output.append(4)
        try:
            output.append(6)
        finally:
            output.append(8)
        output.append(9)

@jump_test(6, 7, [2, 7], (ZeroDivisionError, ''))
def test_jump_in_nested_finally_2(output):
    try:
        output.append(2)
        1.0/0.0
        return
    finally:
        output.append(6)
        output.append(7)
    output.append(8)

@jump_test(6, 11, [2, 11], (ZeroDivisionError, ''))
def test_jump_in_nested_finally_3(output):
    try:
        output.append(2)
        1.0/0.0
        return
    finally:
        output.append(6)
        try:
            output.append(8)
        finally:
            output.append(10)
        output.append(11)
    output.append(12)

@jump_test(3, 4, [1, 4])
def test_jump_infinite_while_loop(output):
    output.append(1)
    while True:
        output.append(3)
    output.append(4)

@jump_test(2, 3, [1, 3])
def test_jump_forwards_out_of_with_block(output):
    with tracecontext(output, 1):
        output.append(2)
    output.append(3)

@jump_test(3, 1, [1, 2, 1, 2, 3, -2])
def test_jump_backwards_out_of_with_block(output):
    output.append(1)
    with tracecontext(output, 2):
        output.append(3)

@jump_test(2, 5, [5])
def test_jump_forwards_out_of_try_finally_block(output):
    try:
        output.append(2)
    finally:
        output.append(4)
    output.append(5)

@jump_test(3, 1, [1, 1, 3, 5])
def test_jump_backwards_out_of_try_finally_block(output):
    output.append(1)
    try:
        output.append(3)
    finally:
        output.append(5)

@jump_test(2, 6, [6])
def test_jump_forwards_out_of_try_except_block(output):
    try:
        output.append(2)
    except:
        output.append(4)
        raise
    output.append(6)

@jump_test(3, 1, [1, 1, 3])
def test_jump_backwards_out_of_try_except_block(output):
    output.append(1)
    try:
        output.append(3)
    except:
        output.append(5)
        raise

@jump_test(5, 7, [4, 7, 8])
def test_jump_between_except_blocks(output):
    try:
        1.0/0.0
    except ZeroDivisionError:
        output.append(4)
        output.append(5)
    except FloatingPointError:
        output.append(7)
    output.append(8)

@jump_test(5, 6, [4, 6, 7])
def test_jump_within_except_block(output):
    try:
        1.0/0.0
    except:
        output.append(4)
        output.append(5)
        output.append(6)
    output.append(7)

@jump_test(2, 4, [1, 4, 5, -4])
def test_jump_across_with(output):
    output.append(1)
    with tracecontext(output, 2):
        output.append(3)
    with tracecontext(output, 4):
        output.append(5)

@jump_test(4, 5, [1, 3, 5, 6])
def test_jump_out_of_with_block_within_for_block(output):
    output.append(1)
    for i in [1]:
        with tracecontext(output, 3):
            output.append(4)
        output.append(5)
    output.append(6)

@jump_test(4, 5, [1, 2, 3, 5, -2, 6])
def test_jump_out_of_with_block_within_with_block(output):
    output.append(1)
    with tracecontext(output, 2):
        with tracecontext(output, 3):
            output.append(4)
        output.append(5)
    output.append(6)

@jump_test(5, 6, [2, 4, 6, 7])
def test_jump_out_of_with_block_within_finally_block(output):
    try:
        output.append(2)
    finally:
        with tracecontext(output, 4):
            output.append(5)
        output.append(6)
    output.append(7)

@jump_test(8, 11, [1, 3, 5, 11, 12])
def test_jump_out_of_complex_nested_blocks(output):
    output.append(1)
    for i in [1]:
        output.append(3)
        for j in [1, 2]:
            output.append(5)
            try:
                for k in [1, 2]:
                    output.append(8)
            finally:
                output.append(10)
        output.append(11)
    output.append(12)

@jump_test(3, 5, [1, 2, 5])
def test_jump_out_of_with_assignment(output):
    output.append(1)
    with tracecontext(output, 2) \
            as x:
        output.append(4)
    output.append(5)

@jump_test(3, 6, [1, 6, 8, 9])
def test_jump_over_return_in_try_finally_block(output):
    output.append(1)
    try:
        output.append(3)
        if not output: # always false
            return
        output.append(6)
    finally:
        output.append(8)
    output.append(9)

@jump_test(5, 8, [1, 3, 8, 10, 11, 13])
def test_jump_over_break_in_try_finally_block(output):
    output.append(1)
    while True:
        output.append(3)
        try:
            output.append(5)
            if not output: # always false
                break
            output.append(8)
        finally:
            output.append(10)
        output.append(11)
        break
    output.append(13)

@jump_test(1, 7, [7, 8])
def test_jump_over_for_block_before_else(output):
    output.append(1)
    if not output:  # always false
        for i in [3]:
            output.append(4)
    else:
        output.append(6)
        output.append(7)
    output.append(8)

# The second set of 'jump' tests are for things that are not allowed:

@jump_test(2, 3, [1], (ValueError, 'after'))
def test_no_jump_too_far_forwards(output):
    output.append(1)
    output.append(2)

@jump_test(2, -2, [1], (ValueError, 'before'))
def test_no_jump_too_far_backwards(output):
    output.append(1)
    output.append(2)

# Test each kind of 'except' line.
@jump_test(2, 3, [4], (ValueError, 'except'))
def test_no_jump_to_except_1(output):
    try:
        output.append(2)
    except:
        output.append(4)
        raise

@jump_test(2, 3, [4], (ValueError, 'except'))
def test_no_jump_to_except_2(output):
    try:
        output.append(2)
    except ValueError:
        output.append(4)
        raise

@jump_test(2, 3, [4], (ValueError, 'except'))
def test_no_jump_to_except_3(output):
    try:
        output.append(2)
    except ValueError as e:
        output.append(4)
        raise e

@jump_test(2, 3, [4], (ValueError, 'except'))
def test_no_jump_to_except_4(output):
    try:
        output.append(2)
    except (ValueError, RuntimeError) as e:
        output.append(4)
        raise e

@jump_test(1, 3, [], (ValueError, 'into'))
def test_no_jump_forwards_into_for_block(output):
    output.append(1)
    for i in 1, 2:
        output.append(3)

@jump_test(3, 2, [2, 2], (ValueError, 'into'))
def test_no_jump_backwards_into_for_block(output):
    for i in 1, 2:
        output.append(2)
    output.append(3)

@jump_test(2, 4, [], (ValueError, 'into'))
def test_no_jump_forwards_into_while_block(output):
    i = 1
    output.append(2)
    while i <= 2:
        output.append(4)
        i += 1

@jump_test(5, 3, [3, 3], (ValueError, 'into'))
def test_no_jump_backwards_into_while_block(output):
    i = 1
    while i <= 2:
        output.append(3)
        i += 1
    output.append(5)

@jump_test(1, 3, [], (ValueError, 'into'))
def test_no_jump_forwards_into_with_block(output):
    output.append(1)
    with tracecontext(output, 2):
        output.append(3)

@jump_test(3, 2, [1, 2, -1], (ValueError, 'into'))
def test_no_jump_backwards_into_with_block(output):
    with tracecontext(output, 1):
        output.append(2)
    output.append(3)

@jump_test(1, 3, [], (ValueError, 'into'))
def test_no_jump_forwards_into_try_finally_block(output):
    output.append(1)
    try:
        output.append(3)
    finally:
        output.append(5)

@jump_test(5, 2, [2, 4], (ValueError, 'into'))
def test_no_jump_backwards_into_try_finally_block(output):
    try:
        output.append(2)
    finally:
        output.append(4)
    output.append(5)

@jump_test(1, 3, [], (ValueError, 'into'))
def test_no_jump_forwards_into_try_except_block(output):
    output.append(1)
    try:
        output.append(3)
    except:
        output.append(5)
        raise

@jump_test(6, 2, [2], (ValueError, 'into'))
def test_no_jump_backwards_into_try_except_block(output):
    try:
        output.append(2)
    except:
        output.append(4)
        raise
    output.append(6)

@jump_test(3, 6, [2, 5, 6], (ValueError, 'finally'))
def test_no_jump_into_finally_block(output):
    try:
        output.append(2)
        output.append(3)
    finally:  # still executed if the jump is failed
        output.append(5)
        output.append(6)
    output.append(7)

@jump_test(1, 5, [], (ValueError, 'finally'))
def test_no_jump_into_finally_block_2(output):
    output.append(1)
    try:
        output.append(3)
    finally:
        output.append(5)

@jump_test(5, 1, [1, 3], (ValueError, 'finally'))
def test_no_jump_out_of_finally_block(output):
    output.append(1)
    try:
        output.append(3)
    finally:
        output.append(5)

@jump_test(3, 5, [1, 2, -2], (ValueError, 'into'))
def test_no_jump_between_with_blocks(output):
    output.append(1)
    with tracecontext(output, 2):
        output.append(3)
    with tracecontext(output, 4):
        output.append(5)

@jump_test(7, 4, [1, 6], (ValueError, 'into'))
def test_no_jump_into_for_block_before_else(output):
    output.append(1)
    if not output:  # always false
        for i in [3]:
            output.append(4)
    else:
        output.append(6)
        output.append(7)
    output.append(8)

@jump_test(2, 3, [1], event='call', error=(ValueError, "can't jump from"
           " the 'call' trace event of a new frame"))
def test_no_jump_from_call(output):
    output.append(1)
    def nested():
        output.append(3)
    nested()
    output.append(5)

@jump_test(2, 1, [1], event='return', error=(ValueError,
           "can only jump from a 'line' trace event"))
def test_no_jump_from_return_event(output):
    output.append(1)
    return

@jump_test(2, 1, [1], event='exception', error=(ValueError,
           "can only jump from a 'line' trace event"))
def test_no_jump_from_exception_event(output):
    output.append(1)
    1 // 0

@jump_test(3, 2, [2], event='return', error=(ValueError,
           "can't jump from a yield statement"))
def test_no_jump_from_yield(output):
    def gen():
        output.append(2)
        yield 3
    next(gen())
    output.append(5)
