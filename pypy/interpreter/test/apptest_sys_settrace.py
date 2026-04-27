# Ported from lib-python/3/test/test_sys_settrace.py
# Converted to pytest apptest style for untranslated testing.
# Skips: @cpython_only tests, async jump tests (non-core), test_very_large_function.

import sys
import gc
import pytest


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

class tracecontext:
    """Context manager that traces its enter and exit."""
    def __init__(self, output, value):
        self.output = output
        self.value = value

    def __enter__(self):
        self.output.append(self.value)

    def __exit__(self, *exc_info):
        self.output.append(-self.value)


class asynctracecontext:
    """Asynchronous context manager that traces its aenter and aexit."""
    def __init__(self, output, value):
        self.output = output
        self.value = value

    async def __aenter__(self):
        self.output.append(self.value)

    async def __aexit__(self, *exc_info):
        self.output.append(-self.value)


async def asynciter(iterable):
    """Convert an iterable to an asynchronous iterator."""
    for x in iterable:
        yield x


class Tracer:
    def __init__(self, trace_line_events=None, trace_opcode_events=None):
        self.trace_line_events = trace_line_events
        self.trace_opcode_events = trace_opcode_events
        self.events = []

    def _reconfigure_frame(self, frame):
        if self.trace_line_events is not None:
            frame.f_trace_lines = self.trace_line_events
        if self.trace_opcode_events is not None:
            frame.f_trace_opcodes = self.trace_opcode_events

    def trace(self, frame, event, arg):
        self._reconfigure_frame(frame)
        self.events.append((frame.f_lineno, event))
        return self.trace

    def traceWithGenexp(self, frame, event, arg):
        self._reconfigure_frame(frame)
        (o for o in [1])
        self.events.append((frame.f_lineno, event))
        return self.trace


def compare_events(line_offset, events, expected_events):
    import difflib
    events = [(l - line_offset, e) for (l, e) in events]
    if events != expected_events:
        raise AssertionError(
            "events did not match expectation:\n" +
            "\n".join(difflib.ndiff([str(x) for x in expected_events],
                                    [str(x) for x in events])))


def run_and_compare(func, expected_events):
    using_gc = gc.isenabled()
    gc.collect()  # collect importlib generators before disabling GC (PyPy has no refcounting)
    gc.disable()
    try:
        tracer = Tracer()
        sys.settrace(tracer.trace)
        try:
            func()
        finally:
            sys.settrace(None)
        compare_events(func.__code__.co_firstlineno, tracer.events, expected_events)
    finally:
        if using_gc:
            gc.enable()


def run_test(func):
    run_and_compare(func, func.events)


def run_test2(func):
    """For functions that take a trace function as argument."""
    using_gc = gc.isenabled()
    gc.disable()
    try:
        tracer = Tracer()
        func(tracer.trace)
        sys.settrace(None)
        compare_events(func.__code__.co_firstlineno, tracer.events, func.events)
    finally:
        if using_gc:
            gc.enable()


# ---------------------------------------------------------------------------
# Functions with associated .events used by trace tests
# ---------------------------------------------------------------------------

def basic():
    return 1

basic.events = [(0, 'call'),
                (1, 'line'),
                (1, 'return')]


def arigo_example0():
    x = 1
    del x
    while 0:
        pass
    x = 1

arigo_example0.events = [(0, 'call'),
                         (1, 'line'),
                         (2, 'line'),
                         (3, 'line'),
                         (5, 'line'),
                         (5, 'return')]


def arigo_example1():
    x = 1
    del x
    if 0:
        pass
    x = 1

arigo_example1.events = [(0, 'call'),
                         (1, 'line'),
                         (2, 'line'),
                         (3, 'line'),
                         (5, 'line'),
                         (5, 'return')]


def arigo_example2():
    x = 1
    del x
    if 1:
        x = 1
    else:
        pass
    return None

arigo_example2.events = [(0, 'call'),
                         (1, 'line'),
                         (2, 'line'),
                         (3, 'line'),
                         (4, 'line'),
                         (7, 'line'),
                         (7, 'return')]


def one_instr_line():
    x = 1
    del x
    x = 1

one_instr_line.events = [(0, 'call'),
                         (1, 'line'),
                         (2, 'line'),
                         (3, 'line'),
                         (3, 'return')]


def no_pop_tops():      # 0
    x = 1               # 1
    for a in range(2):  # 2
        if a:           # 3
            x = 1       # 4
        else:           # 5
            x = 1       # 6

no_pop_tops.events = [(0, 'call'),
                      (1, 'line'),
                      (2, 'line'),
                      (3, 'line'),
                      (6, 'line'),
                      (2, 'line'),
                      (3, 'line'),
                      (4, 'line'),
                      (2, 'line'),
                      (2, 'return')]


def no_pop_blocks():
    y = 1
    while not y:
        bla
    x = 1

no_pop_blocks.events = [(0, 'call'),
                        (1, 'line'),
                        (2, 'line'),
                        (4, 'line'),
                        (4, 'return')]


def _called():  # line -3
    x = 1

def _call():    # line 0
    _called()

_call.events = [(0, 'call'),
                (1, 'line'),
                (-3, 'call'),
                (-2, 'line'),
                (-2, 'return'),
                (1, 'return')]


def _raises():
    raise Exception

def _test_raise():
    try:
        _raises()
    except Exception:
        pass

_test_raise.events = [(0, 'call'),
                      (1, 'line'),
                      (2, 'line'),
                      (-3, 'call'),
                      (-2, 'line'),
                      (-2, 'exception'),
                      (-2, 'return'),
                      (2, 'exception'),
                      (3, 'line'),
                      (4, 'line'),
                      (4, 'return')]


def _settrace_and_return(tracefunc):
    sys.settrace(tracefunc)
    sys._getframe().f_back.f_trace = tracefunc

def settrace_and_return(tracefunc):
    _settrace_and_return(tracefunc)

settrace_and_return.events = [(1, 'return')]


def _settrace_and_raise(tracefunc):
    sys.settrace(tracefunc)
    sys._getframe().f_back.f_trace = tracefunc
    raise RuntimeError

def settrace_and_raise(tracefunc):
    try:
        _settrace_and_raise(tracefunc)
    except RuntimeError:
        pass

settrace_and_raise.events = [(2, 'exception'),
                             (3, 'line'),
                             (4, 'line'),
                             (4, 'return')]


def ireturn_example():
    a = 5
    b = 5
    if a == b:
        b = a+1
    else:
        pass

ireturn_example.events = [(0, 'call'),
                          (1, 'line'),
                          (2, 'line'),
                          (3, 'line'),
                          (4, 'line'),
                          (4, 'return')]


def tightloop_example():
    items = range(0, 3)
    try:
        i = 0
        while 1:
            b = items[i]; i+=1
    except IndexError:
        pass

tightloop_example.events = [(0, 'call'),
                            (1, 'line'),
                            (2, 'line'),
                            (3, 'line'),
                            (4, 'line'),
                            (5, 'line'),
                            (4, 'line'),
                            (5, 'line'),
                            (4, 'line'),
                            (5, 'line'),
                            (4, 'line'),
                            (5, 'line'),
                            (5, 'exception'),
                            (6, 'line'),
                            (7, 'line'),
                            (7, 'return')]


def tighterloop_example():
    items = range(1, 4)
    try:
        i = 0
        while 1: i = items[i]
    except IndexError:
        pass

tighterloop_example.events = [(0, 'call'),
                              (1, 'line'),
                              (2, 'line'),
                              (3, 'line'),
                              (4, 'line'),
                              (4, 'line'),
                              (4, 'line'),
                              (4, 'line'),
                              (4, 'exception'),
                              (5, 'line'),
                              (6, 'line'),
                              (6, 'return')]


def generator_function():
    try:
        yield True
        "continued"
    finally:
        "finally"

def generator_example():
    # any() will leave the generator before its end
    x = any(generator_function()); gc.collect()
    for x in range(10):
        y = x

generator_example.events = ([(0, 'call'),
                              (2, 'line'),
                              (-7, 'call'),
                              (-6, 'line'),
                              (-5, 'line'),
                              (-5, 'return'),
                              (-5, 'call'),
                              (-5, 'exception'),
                              (-2, 'line'),
                              (-2, 'return')] +
                             [(3, 'line'), (4, 'line')] * 10 +
                             [(3, 'line'), (3, 'return')])


# ---------------------------------------------------------------------------
# TraceTestCase tests
# ---------------------------------------------------------------------------

def test_set_and_retrieve_none():
    sys.settrace(None)
    assert sys.gettrace() is None


def test_set_and_retrieve_func():
    def fn(*args):
        pass
    sys.settrace(fn)
    try:
        assert sys.gettrace() is fn
    finally:
        sys.settrace(None)


def test_01_basic():
    run_test(basic)

def test_02_arigo0():
    run_test(arigo_example0)

def test_02_arigo1():
    run_test(arigo_example1)

def test_02_arigo2():
    run_test(arigo_example2)

def test_03_one_instr():
    run_test(one_instr_line)

def test_04_no_pop_blocks():
    run_test(no_pop_blocks)

def test_05_no_pop_tops():
    run_test(no_pop_tops)

def test_06_call():
    run_test(_call)

def test_07_raise():
    run_test(_test_raise)

def test_08_settrace_and_return():
    run_test2(settrace_and_return)

def test_09_settrace_and_raise():
    run_test2(settrace_and_raise)

def test_10_ireturn():
    run_test(ireturn_example)

def test_11_tightloop():
    run_test(tightloop_example)

def test_12_tighterloop():
    run_test(tighterloop_example)


def test_13_genexp():
    using_gc = gc.isenabled()
    if not using_gc:
        gc.enable()
        gc.collect()
    try:
        run_test(generator_example)
        tracer = Tracer()
        sys.settrace(tracer.traceWithGenexp)
        generator_example()
        sys.settrace(None)
        compare_events(generator_example.__code__.co_firstlineno,
                       tracer.events, generator_example.events)
    finally:
        if not using_gc:
            gc.disable()


def test_14_onliner_if():
    def onliners():
        if True: x=False
        else: x=True
        return 0
    run_and_compare(onliners,
        [(0, 'call'),
         (1, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_15_loops():
    def for_example():
        for x in range(2):
            pass
    run_and_compare(for_example,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (1, 'line'),
         (2, 'line'),
         (1, 'line'),
         (1, 'return')])

    def while_example():
        # While expression should be traced on every loop
        x = 2
        while x > 0:
            x -= 1
    run_and_compare(while_example,
        [(0, 'call'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (3, 'line'),
         (4, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_16_blank_lines():
    namespace = {}
    exec("def f():\n" + "\n" * 256 + "    pass", namespace)
    run_and_compare(namespace["f"],
        [(0, 'call'),
         (257, 'line'),
         (257, 'return')])


def test_17_none_f_trace():
    def func():
        sys._getframe().f_trace = None
        lineno = 2
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line')])


def test_18_except_with_name():
    def func():
        try:
            try:
                raise Exception
            except Exception as e:
                raise
                x = "Something"
                y = "Something"
        except Exception:
            pass
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (4, 'line'),
         (5, 'line'),
         (8, 'line'),
         (9, 'line'),
         (9, 'return')])


def test_19_except_with_finally():
    def func():
        try:
            try:
                raise Exception
            finally:
                y = "Something"
        except Exception:
            b = 23
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (5, 'line'),
         (6, 'line'),
         (7, 'line'),
         (7, 'return')])


def test_21_repeated_pass():
    def func():
        pass
        pass
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (2, 'return')])


def test_loop_in_try_except():
    def func():
        try:
            for i in []: pass
            return 1
        except:
            return 2
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_try_except_no_exception():
    def func():
        try:
            2
        except:
            4
        else:
            6
            if False:
                8
            else:
                10
            if func.__name__ == 'Fred':
                12
        finally:
            14
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (6, 'line'),
         (7, 'line'),
         (10, 'line'),
         (11, 'line'),
         (14, 'line'),
         (14, 'return')])


def test_try_exception_in_else():
    def func():
        try:
            try:
                3
            except:
                5
            else:
                7
                raise Exception
            finally:
                10
        except:
            12
        finally:
            14
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (7, 'line'),
         (8, 'line'),
         (8, 'exception'),
         (10, 'line'),
         (11, 'line'),
         (12, 'line'),
         (14, 'line'),
         (14, 'return')])


def test_nested_loops():
    def func():
        for i in range(2):
            for j in range(2):
                a = i + j
        return a == 1
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (2, 'line'),
         (3, 'line'),
         (2, 'line'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (2, 'line'),
         (3, 'line'),
         (2, 'line'),
         (1, 'line'),
         (4, 'line'),
         (4, 'return')])


def test_if_break():
    def func():
        seq = [1, 0]
        while seq:
            n = seq.pop()
            if n:
                break
        else:
            n = 99
        return n
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (8, 'line'),
         (8, 'return')])


def test_break_through_finally():
    def func():
        a, c, d, i = 1, 1, 1, 99
        try:
            for i in range(3):
                try:
                    a = 5
                    if i > 0:
                        break
                    a = 8
                finally:
                    c = 10
        except:
            d = 12
        assert a == 5 and c == 10 and d == 1
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (6, 'line'),
         (8, 'line'),
         (10, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (6, 'line'),
         (7, 'line'),
         (10, 'line'),
         (13, 'line'),
         (13, 'return')])


def test_continue_through_finally():
    def func():
        a, b, c, d, i = 1, 1, 1, 1, 99
        try:
            for i in range(2):
                try:
                    a = 5
                    if i > 0:
                        continue
                    b = 8
                finally:
                    c = 10
        except:
            d = 12
        assert (a, b, c, d) == (5, 8, 10, 1)
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (6, 'line'),
         (8, 'line'),
         (10, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (6, 'line'),
         (7, 'line'),
         (10, 'line'),
         (3, 'line'),
         (13, 'line'),
         (13, 'return')])


def test_return_through_finally():
    def func():
        try:
            return 2
        finally:
            4
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (4, 'line'),
         (4, 'return')])


def test_try_except_with_wrong_type():
    def func():
        try:
            2/0
        except IndexError:
            4
        finally:
            return 6
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (2, 'exception'),
         (3, 'line'),
         (6, 'line'),
         (6, 'return')])


def test_break_to_continue1():
    def func():
        TRUE = 1
        x = [1]
        while x:
            x.pop()
            while TRUE:
                break
            continue
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (6, 'line'),
         (7, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_break_to_continue2():
    def func():
        TRUE = 1
        x = [1]
        while x:
            x.pop()
            while TRUE:
                break
            else:
                continue
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (6, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_break_to_break():
    def func():
        TRUE = 1
        while TRUE:
            while TRUE:
                break
            break
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (5, 'line'),
         (5, 'return')])


def test_nested_ifs():
    def func():
        a = b = 1
        if a == 1:
            if b == 1:
                x = 4
            else:
                y = 6
        else:
            z = 8
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (4, 'line'),
         (4, 'return')])


def test_nested_ifs_with_and():
    A = B = True
    C = False

    def func():
        if A:
            if B:
                if C:
                    if D:
                        return False
            else:
                return False
        elif E and F:
            return True
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_nested_try_if():
    def func():
        x = "hello"
        try:
            3/0
        except ZeroDivisionError:
            if x == 'raise':
                raise ValueError()
        f = 7
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (4, 'line'),
         (5, 'line'),
         (7, 'line'),
         (7, 'return')])


def test_if_false_in_with():
    class C:
        def __enter__(self):
            return self
        def __exit__(*args):
            pass

    def func():
        with C():
            if False:
                pass
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (-5, 'call'),
         (-4, 'line'),
         (-4, 'return'),
         (2, 'line'),
         (1, 'line'),
         (-3, 'call'),
         (-2, 'line'),
         (-2, 'return'),
         (1, 'return')])


def test_if_false_in_try_except():
    def func():
        try:
            if False:
                pass
        except Exception:
            X
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (2, 'return')])


def test_implicit_return_in_class():
    def func():
        class A:
            if 3 < 9:
                a = 1
            else:
                a = 2
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (1, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'return'),
         (1, 'return')])


def test_try_in_try():
    def func():
        try:
            try:
                pass
            except Exception as ex:
                pass
        except Exception:
            pass
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_try_in_try_with_exception():
    def func():
        try:
            try:
                raise TypeError
            except ValueError as ex:
                5
        except TypeError:
            7
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (4, 'line'),
         (6, 'line'),
         (7, 'line'),
         (7, 'return')])

    def func2():
        try:
            try:
                raise ValueError
            except ValueError as ex:
                5
        except TypeError:
            7
    run_and_compare(func2,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (4, 'line'),
         (5, 'line'),
         (5, 'return')])


def test_if_in_if_in_if():
    def func(a=0, p=1, z=1):
        if p:
            if a:
                if z:
                    pass
                else:
                    pass
        else:
            pass
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (2, 'return')])


def test_early_exit_with():
    class C:
        def __enter__(self):
            return self
        def __exit__(*args):
            pass

    def func_break():
        for i in (1,2):
            with C():
                break
        pass

    def func_return():
        with C():
            return

    run_and_compare(func_break,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (-5, 'call'),
         (-4, 'line'),
         (-4, 'return'),
         (3, 'line'),
         (2, 'line'),
         (-3, 'call'),
         (-2, 'line'),
         (-2, 'return'),
         (4, 'line'),
         (4, 'return')])

    run_and_compare(func_return,
        [(0, 'call'),
         (1, 'line'),
         (-11, 'call'),
         (-10, 'line'),
         (-10, 'return'),
         (2, 'line'),
         (1, 'line'),
         (-9, 'call'),
         (-8, 'line'),
         (-8, 'return'),
         (1, 'return')])


def test_flow_converges_on_same_line():
    def foo(x):
        if x:
            try:
                1/(x - 1)
            except ZeroDivisionError:
                pass
        return x

    def func():
        for i in range(2):
            foo(i)
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (-8, 'call'),
         (-7, 'line'),
         (-2, 'line'),
         (-2, 'return'),
         (1, 'line'),
         (2, 'line'),
         (-8, 'call'),
         (-7, 'line'),
         (-6, 'line'),
         (-5, 'line'),
         (-5, 'exception'),
         (-4, 'line'),
         (-3, 'line'),
         (-2, 'line'),
         (-2, 'return'),
         (1, 'line'),
         (1, 'return')])


def test_no_tracing_of_named_except_cleanup():
    def func():
        x = 0
        try:
            1/x
        except ZeroDivisionError as error:
            if x:
                raise
        return "done"
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (4, 'line'),
         (5, 'line'),
         (7, 'line'),
         (7, 'return')])


def test_tracing_exception_raised_in_with():
    class NullCtx:
        def __enter__(self):
            return self
        def __exit__(self, *excinfo):
            pass

    def func():
        try:
            with NullCtx():
                1/0
        except ZeroDivisionError:
            pass
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (-5, 'call'),
         (-4, 'line'),
         (-4, 'return'),
         (3, 'line'),
         (3, 'exception'),
         (2, 'line'),
         (-3, 'call'),
         (-2, 'line'),
         (-2, 'return'),
         (4, 'line'),
         (5, 'line'),
         (5, 'return')])


def test_try_except_star_no_exception():
    def func():
        try:
            2
        except* Exception:
            4
        else:
            6
            if False:
                8
            else:
                10
            if func.__name__ == 'Fred':
                12
        finally:
            14
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (6, 'line'),
         (7, 'line'),
         (10, 'line'),
         (11, 'line'),
         (14, 'line'),
         (14, 'return')])


def test_try_except_star_named_no_exception():
    def func():
        try:
            2
        except* Exception as e:
            4
        else:
            6
        finally:
            8
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (6, 'line'),
         (8, 'line'),
         (8, 'return')])


def test_try_except_star_exception_caught():
    def func():
        try:
            raise ValueError(2)
        except* ValueError:
            4
        else:
            6
        finally:
            8
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (2, 'exception'),
         (3, 'line'),
         (4, 'line'),
         (8, 'line'),
         (8, 'return')])


def test_try_except_star_named_exception_caught():
    def func():
        try:
            raise ValueError(2)
        except* ValueError as e:
            4
        else:
            6
        finally:
            8
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (2, 'exception'),
         (3, 'line'),
         (4, 'line'),
         (8, 'line'),
         (8, 'return')])


def test_try_except_star_exception_not_caught():
    def func():
        try:
            try:
                raise ValueError(3)
            except* TypeError:
                5
        except ValueError:
            7
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (4, 'line'),
         (6, 'line'),
         (7, 'line'),
         (7, 'return')])


def test_try_except_star_named_exception_not_caught():
    def func():
        try:
            try:
                raise ValueError(3)
            except* TypeError as e:
                5
        except ValueError:
            7
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'exception'),
         (4, 'line'),
         (6, 'line'),
         (7, 'line'),
         (7, 'return')])


def test_notrace_lambda():
    def func():
        1
        lambda x: 2
        3
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'return')])


def test_class_creation_with_docstrings():
    def func():
        class Class_1:
            ''' the docstring. 2'''
            def __init__(self):
                ''' Another docstring. 4'''
                self.a = 5
    run_and_compare(func,
        [(0, 'call'),
         (1, 'line'),
         (1, 'call'),
         (1, 'line'),
         (2, 'line'),
         (3, 'line'),
         (3, 'return'),
         (1, 'return')])


def test_settrace_error():
    raised = False
    def error_once(frame, event, arg):
        nonlocal raised
        if not raised:
            raised = True
            raise Exception
        return error_once

    try:
        sys._getframe().f_trace = error_once
        sys.settrace(error_once)
        len([])
    except Exception as ex:
        count = 0
        tb = ex.__traceback__
        while tb:
            if tb.tb_frame.f_code.co_name == "test_settrace_error":
                count += 1
            tb = tb.tb_next
        if count == 0:
            raise AssertionError("Traceback is missing frame")
        elif count > 1:
            raise AssertionError("Traceback has frame more than once")
    else:
        raise AssertionError("No exception raised")
    finally:
        sys.settrace(None)


# ---------------------------------------------------------------------------
# RaisingTraceFuncTestCase tests
# ---------------------------------------------------------------------------

def _raiser(raiseOnEvent):
    def trace(frame, event, arg):
        if event == raiseOnEvent:
            raise ValueError
        return trace
    return trace

def _f_for_raising(raiseOnEvent):
    if raiseOnEvent == 'exception':
        x = 0
        y = 1/x
    else:
        return 1

def _run_test_for_event(event):
    trace = _raiser(event)
    try:
        for i in range(sys.getrecursionlimit() + 1):
            sys.settrace(trace)
            try:
                _f_for_raising(event)
            except ValueError:
                pass
            else:
                raise AssertionError("exception not raised!")
    except RuntimeError:
        raise AssertionError("recursion counter not reset")
    finally:
        sys.settrace(None)

def test_raising_on_call():
    _run_test_for_event('call')

def test_raising_on_line():
    _run_test_for_event('line')

def test_raising_on_return():
    _run_test_for_event('return')

def test_raising_on_exception():
    _run_test_for_event('exception')


def test_raising_trash_stack():
    def f():
        for i in range(5):
            print(i)

    def g(frame, why, extra):
        if (why == 'line' and
            frame.f_lineno == f.__code__.co_firstlineno + 2):
            raise RuntimeError("i am crashing")
        return g

    sys.settrace(g)
    try:
        f()
    except RuntimeError:
        gc.collect()
    else:
        raise AssertionError("exception not propagated")
    finally:
        sys.settrace(None)


def test_raising_exception_arguments():
    def f():
        x = 0
        x.no_such_attr

    results = []
    def g(frame, event, arg):
        if event == 'exception':
            type_, exception, trace = arg
            results.append(isinstance(exception, Exception))
        return g

    existing = sys.gettrace()
    try:
        sys.settrace(g)
        try:
            f()
        except AttributeError:
            pass
    finally:
        sys.settrace(existing)
    assert results and all(results)


def test_raising_line_event_raises_before_opcode_event():
    exception = ValueError("BOOM!")
    def trace(frame, event, arg):
        if event == "line":
            raise exception
        frame.f_trace_opcodes = True
        return trace
    def f():
        pass
    with pytest.raises(ValueError) as caught:
        sys.settrace(trace)
        f()
    assert caught.value is exception
    sys.settrace(None)


# ---------------------------------------------------------------------------
# JumpTestCase infrastructure
# ---------------------------------------------------------------------------

class JumpTracer:
    """Defines a trace function that jumps from one place to another."""

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
        if (self.firstLine is None and frame.f_code == self.code and
                event == 'line'):
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


# PyPy uses "body of a with statement" in the error message
_no_jump_into_with_error = (ValueError, "body of a with statement")


def run_jump_test(func, jumpFrom, jumpTo, expected, error=None, event='line'):
    tracer = JumpTracer(func, jumpFrom, jumpTo, event)
    sys.settrace(tracer.trace)
    output = []
    try:
        if error is None:
            func(output)
        else:
            exc_type, exc_msg = error
            with pytest.raises(exc_type, match=exc_msg):
                func(output)
    finally:
        sys.settrace(None)
    assert output == expected, "Expected %r, got %r" % (expected, output)


def run_jump_async_test(func, jumpFrom, jumpTo, expected, error=None, event='line'):
    import asyncio
    tracer = JumpTracer(func, jumpFrom, jumpTo, event)
    sys.settrace(tracer.trace)
    output = []
    try:
        if error is None:
            asyncio.run(func(output))
        else:
            exc_type, exc_msg = error
            with pytest.raises(exc_type, match=exc_msg):
                asyncio.run(func(output))
    finally:
        sys.settrace(None)
    assert output == expected, "Expected %r, got %r" % (expected, output)


def no_jump_to_non_integers(output):
    try:
        output.append(2)
    except ValueError as e:
        output.append('integer' in str(e))


def no_jump_without_trace_function():
    try:
        previous_frame = sys._getframe().f_back
        previous_frame.f_lineno = previous_frame.f_lineno
    except ValueError as e:
        if 'trace' not in str(e):
            raise
    else:
        raise AssertionError("Trace-function-less jump failed to fail")


# ---------------------------------------------------------------------------
# JumpTestCase tests (allowed jumps)
# ---------------------------------------------------------------------------

def test_jump_simple_forwards():
    def func(output):
        output.append(1)
        output.append(2)
        output.append(3)
    run_jump_test(func, 1, 3, [3])

def test_jump_simple_backwards():
    def func(output):
        output.append(1)
        output.append(2)
    run_jump_test(func, 2, 1, [1, 1, 2])

def test_jump_is_none_forwards():
    def func(output):
        x = None
        if x is None:
            output.append(3)
        else:
            output.append(5)
    run_jump_test(func, 1, 4, [5])

def test_jump_is_none_backwards():
    def func(output):
        x = None
        if x is None:
            output.append(3)
        else:
            output.append(5)
        output.append(6)
    run_jump_test(func, 6, 5, [3, 5, 6])

def test_jump_is_not_none_forwards():
    def func(output):
        x = None
        if x is not None:
            output.append(3)
        else:
            output.append(5)
    run_jump_test(func, 1, 4, [5])

def test_jump_is_not_none_backwards():
    def func(output):
        x = None
        if x is not None:
            output.append(3)
        else:
            output.append(5)
        output.append(6)
    run_jump_test(func, 6, 5, [5, 5, 6])

def test_jump_out_of_block_forwards():
    def func(output):
        for i in 1, 2:
            output.append(2)
            for j in [3]:
                output.append(4)
        output.append(5)
    run_jump_test(func, 3, 5, [2, 5])

def test_jump_out_of_block_backwards():
    def func(output):
        output.append(1)
        for i in [1]:
            output.append(3)
            for j in [2]:
                output.append(5)
            output.append(6)
        output.append(7)
    run_jump_test(func, 6, 1, [1, 3, 5, 1, 3, 5, 6, 7])

def test_jump_to_codeless_line():
    def func(output):
        output.append(1)
        # Jumping to this line should skip to the next one.
        output.append(3)
    run_jump_test(func, 1, 2, [3])

def test_jump_to_same_line():
    def func(output):
        output.append(1)
        output.append(2)
        output.append(3)
    run_jump_test(func, 2, 2, [1, 2, 3])

def test_jump_in_nested_finally():
    def func(output):
        try:
            output.append(2)
        finally:
            output.append(4)
            try:
                output.append(6)
            finally:
                output.append(8)
            output.append(9)
    run_jump_test(func, 4, 9, [2, 9])

def test_jump_in_nested_finally_2():
    def func(output):
        try:
            output.append(2)
            1/0
            return
        finally:
            output.append(6)
            output.append(7)
        output.append(8)
    run_jump_test(func, 6, 7, [2, 7], (ZeroDivisionError, ''))

def test_jump_in_nested_finally_3():
    def func(output):
        try:
            output.append(2)
            1/0
            return
        finally:
            output.append(6)
            try:
                output.append(8)
            finally:
                output.append(10)
            output.append(11)
        output.append(12)
    run_jump_test(func, 6, 11, [2, 11], (ZeroDivisionError, ''))

def test_no_jump_infinite_while_loop():
    def func(output):
        output.append(1)
        while True:
            output.append(3)
        output.append(4)
    run_jump_test(func, 3, 4, [1], (ValueError, 'after'))

def test_jump_forwards_into_while_block():
    def func(output):
        i = 1
        output.append(2)
        while i <= 2:
            output.append(4)
            i += 1
    run_jump_test(func, 2, 4, [4, 4])

def test_jump_backwards_into_while_block():
    def func(output):
        i = 1
        while i <= 2:
            output.append(3)
            i += 1
        output.append(5)
    run_jump_test(func, 5, 3, [3, 3, 3, 5])

def test_jump_forwards_out_of_with_block():
    def func(output):
        with tracecontext(output, 1):
            output.append(2)
        output.append(3)
    run_jump_test(func, 2, 3, [1, 3])

def test_jump_backwards_out_of_with_block():
    def func(output):
        output.append(1)
        with tracecontext(output, 2):
            output.append(3)
    run_jump_test(func, 3, 1, [1, 2, 1, 2, 3, -2])

def test_jump_forwards_out_of_try_finally_block():
    def func(output):
        try:
            output.append(2)
        finally:
            output.append(4)
        output.append(5)
    run_jump_test(func, 2, 5, [5])

def test_jump_backwards_out_of_try_finally_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        finally:
            output.append(5)
    run_jump_test(func, 3, 1, [1, 1, 3, 5])

def test_jump_forwards_out_of_try_except_block():
    def func(output):
        try:
            output.append(2)
        except:
            output.append(4)
            raise
        output.append(6)
    run_jump_test(func, 2, 6, [6])

def test_jump_backwards_out_of_try_except_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        except:
            output.append(5)
            raise
    run_jump_test(func, 3, 1, [1, 1, 3])

def test_jump_between_except_blocks():
    def func(output):
        try:
            1/0
        except ZeroDivisionError:
            output.append(4)
            output.append(5)
        except FloatingPointError:
            output.append(7)
        output.append(8)
    run_jump_test(func, 5, 7, [4, 7, 8])

def test_jump_from_except_to_finally():
    def func(output):
        try:
            1/0
        except ZeroDivisionError:
            output.append(4)
            output.append(5)
        finally:
            output.append(7)
        output.append(8)
    run_jump_test(func, 5, 7, [4, 7, 8])

def test_jump_within_except_block():
    def func(output):
        try:
            1/0
        except:
            output.append(4)
            output.append(5)
            output.append(6)
        output.append(7)
    run_jump_test(func, 5, 6, [4, 6, 7])

def test_jump_over_try_except():
    def func(output):
        output.append(1)
        try:
            1 / 0
        except ZeroDivisionError as e:
            output.append(5)
        x = 42
    run_jump_test(func, 6, 1, [1, 5, 1, 5])

def test_jump_across_with():
    def func(output):
        output.append(1)
        with tracecontext(output, 2):
            output.append(3)
        with tracecontext(output, 4):
            output.append(5)
    run_jump_test(func, 2, 4, [1, 4, 5, -4])

def test_jump_out_of_with_block_within_for_block():
    def func(output):
        output.append(1)
        for i in [1]:
            with tracecontext(output, 3):
                output.append(4)
            output.append(5)
        output.append(6)
    run_jump_test(func, 4, 5, [1, 3, 5, 6])

def test_jump_out_of_with_block_within_with_block():
    def func(output):
        output.append(1)
        with tracecontext(output, 2):
            with tracecontext(output, 3):
                output.append(4)
            output.append(5)
        output.append(6)
    run_jump_test(func, 4, 5, [1, 2, 3, 5, -2, 6])

def test_jump_out_of_with_block_within_finally_block():
    def func(output):
        try:
            output.append(2)
        finally:
            with tracecontext(output, 4):
                output.append(5)
            output.append(6)
        output.append(7)
    run_jump_test(func, 5, 6, [2, 4, 6, 7])

def test_jump_out_of_complex_nested_blocks():
    def func(output):
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
    run_jump_test(func, 8, 11, [1, 3, 5, 11, 12])

def test_jump_out_of_with_assignment():
    def func(output):
        output.append(1)
        with tracecontext(output, 2) \
                as x:
            output.append(4)
        output.append(5)
    run_jump_test(func, 3, 5, [1, 2, 5])

def test_jump_over_return_in_try_finally_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
            if not output:
                return
            output.append(6)
        finally:
            output.append(8)
        output.append(9)
    run_jump_test(func, 3, 6, [1, 6, 8, 9])

def test_jump_over_break_in_try_finally_block():
    def func(output):
        output.append(1)
        while True:
            output.append(3)
            try:
                output.append(5)
                if not output:
                    break
                output.append(8)
            finally:
                output.append(10)
            output.append(11)
            break
        output.append(13)
    run_jump_test(func, 5, 8, [1, 3, 8, 10, 11, 13])

def test_jump_over_for_block_before_else():
    def func(output):
        output.append(1)
        if not output:
            for i in [3]:
                output.append(4)
        else:
            output.append(6)
            output.append(7)
        output.append(8)
    run_jump_test(func, 1, 7, [7, 8])

def test_jump_forwards_into_try_finally_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        finally:
            output.append(5)
    run_jump_test(func, 1, 3, [3, 5])

def test_jump_backwards_into_try_finally_block():
    def func(output):
        try:
            output.append(2)
        finally:
            output.append(4)
        output.append(5)
    run_jump_test(func, 5, 2, [2, 4, 2, 4, 5])

def test_jump_forwards_into_try_except_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        except:
            output.append(5)
            raise
    run_jump_test(func, 1, 3, [3])

def test_jump_backwards_into_try_except_block():
    def func(output):
        try:
            output.append(2)
        except:
            output.append(4)
            raise
        output.append(6)
    run_jump_test(func, 6, 2, [2, 2, 6])

def test_jump_between_except_blocks_2():
    def func(output):
        try:
            1/0
        except ZeroDivisionError:
            output.append(4)
            output.append(5)
        except FloatingPointError as e:
            output.append(7)
        output.append(8)
    run_jump_test(func, 5, 7, [4, 7, 8])

def test_jump_into_finally_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        finally:
            output.append(5)
    run_jump_test(func, 1, 5, [5])

def test_jump_into_finally_block_from_try_block():
    def func(output):
        try:
            output.append(2)
            output.append(3)
        finally:
            output.append(5)
            output.append(6)
        output.append(7)
    run_jump_test(func, 3, 6, [2, 6, 7])

def test_jump_out_of_finally_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        finally:
            output.append(5)
    run_jump_test(func, 5, 1, [1, 3, 1, 3, 5])

def test_jump_between_with_blocks():
    def func(output):
        output.append(1)
        with tracecontext(output, 2):
            output.append(3)
        with tracecontext(output, 4):
            output.append(5)
    run_jump_test(func, 3, 5, [1, 2, 5, -2])


# ---------------------------------------------------------------------------
# JumpTestCase tests (not allowed)
# ---------------------------------------------------------------------------

def test_no_jump_too_far_forwards():
    def func(output):
        output.append(1)
        output.append(2)
    run_jump_test(func, 2, 3, [1], (ValueError, 'after'))

def test_no_jump_too_far_backwards():
    def func(output):
        output.append(1)
        output.append(2)
    run_jump_test(func, 2, -2, [1], (ValueError, 'before'))

def test_no_jump_to_except_1():
    def func(output):
        try:
            output.append(2)
        except:
            output.append(4)
            raise
    run_jump_test(func, 2, 3, [4], (ValueError, 'except'))

def test_no_jump_to_except_2():
    def func(output):
        try:
            output.append(2)
        except ValueError:
            output.append(4)
            raise
    run_jump_test(func, 2, 3, [4], (ValueError, 'except'))

def test_no_jump_to_except_3():
    def func(output):
        try:
            output.append(2)
        except ValueError as e:
            output.append(4)
            raise e
    run_jump_test(func, 2, 3, [4], (ValueError, 'except'))

def test_no_jump_to_except_4():
    def func(output):
        try:
            output.append(2)
        except (ValueError, RuntimeError) as e:
            output.append(4)
            raise e
    run_jump_test(func, 2, 3, [4], (ValueError, 'except'))

def test_no_jump_forwards_into_for_block():
    def func(output):
        output.append(1)
        for i in 1, 2:
            output.append(3)
    run_jump_test(func, 1, 3, [], (ValueError, 'into'))

def test_no_jump_backwards_into_for_block():
    def func(output):
        for i in 1, 2:
            output.append(2)
        output.append(3)
    run_jump_test(func, 3, 2, [2, 2], (ValueError, 'into'))

def test_no_jump_forwards_into_with_block():
    def func(output):
        output.append(1)
        with tracecontext(output, 2):
            output.append(3)
    run_jump_test(func, 1, 3, [], _no_jump_into_with_error)

def test_no_jump_backwards_into_with_block():
    def func(output):
        with tracecontext(output, 1):
            output.append(2)
        output.append(3)
    run_jump_test(func, 3, 2, [1, 2, -1], _no_jump_into_with_error)

def test_no_jump_into_bare_except_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        except:
            output.append(5)
    run_jump_test(func, 1, 5, [], (ValueError, "can't jump into an 'except' block as there's no exception"))

def test_no_jump_into_qualified_except_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
        except Exception:
            output.append(5)
    run_jump_test(func, 1, 5, [], (ValueError, "can't jump into an 'except' block as there's no exception"))

def test_no_jump_into_bare_except_block_from_try_block():
    def func(output):
        try:
            output.append(2)
            output.append(3)
        except:
            output.append(5)
            output.append(6)
            raise
        output.append(8)
    run_jump_test(func, 3, 6, [2, 5, 6], (ValueError, "can't jump into an 'except' block as there's no exception"))

def test_no_jump_into_qualified_except_block_from_try_block():
    def func(output):
        try:
            output.append(2)
            output.append(3)
        except ZeroDivisionError:
            output.append(5)
            output.append(6)
            raise
        output.append(8)
    run_jump_test(func, 3, 6, [2], (ValueError, "can't jump into an 'except' block as there's no exception"))

def test_jump_out_of_bare_except_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
            1/0
        except:
            output.append(6)
            output.append(7)
    run_jump_test(func, 7, 1, [1, 3, 6, 1, 3, 6, 7])

def test_jump_out_of_qualified_except_block():
    def func(output):
        output.append(1)
        try:
            output.append(3)
            1/0
        except Exception:
            output.append(6)
            output.append(7)
    run_jump_test(func, 7, 1, [1, 3, 6, 1, 3, 6, 7])

def test_no_jump_over_return_out_of_finally_block():
    def func(output):
        try:
            output.append(2)
        finally:
            output.append(4)
            output.append(5)
            return
        output.append(7)
    run_jump_test(func, 5, 7, [2, 4], (ValueError, 'after'))

def test_no_jump_into_for_block_before_else():
    def func(output):
        output.append(1)
        if not output:
            for i in [3]:
                output.append(4)
        else:
            output.append(6)
            output.append(7)
        output.append(8)
    run_jump_test(func, 7, 4, [1, 6], (ValueError, 'into'))

def test_no_jump_to_non_integers():
    run_jump_test(no_jump_to_non_integers, 2, "Spam", [True])

def test_no_jump_without_trace_function():
    no_jump_without_trace_function()

def test_large_function():
    d = {}
    exec("""def f(output):        # line 0
        x = 0                     # line 1
        y = 1                     # line 2
        '''                       # line 3
        %s                        # lines 4-1004
        '''                       # line 1005
        x += 1                    # line 1006
        output.append(x)          # line 1007
        return""" % ('\n' * 1000,), d)
    f = d['f']
    run_jump_test(f, 2, 1007, [0])

def test_jump_to_firstlineno():
    code = compile("""
# Comments don't count.
output.append(2)  # firstlineno is here.
output.append(3)
output.append(4)
""", "<fake module>", "exec")
    class fake_function:
        __code__ = code
    tracer = JumpTracer(fake_function, 4, 1)
    sys.settrace(tracer.trace)
    namespace = {"output": []}
    exec(code, namespace)
    sys.settrace(None)
    assert namespace["output"] == [2, 3, 2, 3, 4]

def test_no_jump_from_call():
    def func(output):
        output.append(1)
        def nested():
            output.append(3)
        nested()
        output.append(5)
    run_jump_test(func, 2, 3, [1], event='call',
                  error=(ValueError, "can't jump from the 'call' trace event of a new frame"))

def test_no_jump_from_return_event():
    def func(output):
        output.append(1)
        return
    run_jump_test(func, 2, 1, [1], event='return',
                  error=(ValueError, "can only jump from a 'line' trace event"))

def test_no_jump_from_exception_event():
    def func(output):
        output.append(1)
        1 / 0
    run_jump_test(func, 2, 1, [1], event='exception',
                  error=(ValueError, "can only jump from a 'line' trace event"))

def test_jump_from_yield():
    def func(output):
        def gen():
            output.append(2)
            yield 3
        next(gen())
        output.append(5)
    run_jump_test(func, 3, 2, [2, 5], event='return')

def test_jump_forward_over_listcomp():
    def func(output):
        output.append(1)
        x = [i for i in range(10)]
        output.append(3)
    run_jump_test(func, 2, 3, [1, 3])

def test_jump_backward_over_listcomp():
    def func(output):
        a = 1
        x = [i for i in range(10)]
        c = 3
    run_jump_test(func, 3, 1, [])

def test_jump_backward_over_listcomp_v2():
    def func(output):
        flag = False
        output.append(2)
        if flag:
            return
        x = [i for i in range(5)]
        flag = 6
        output.append(7)
        output.append(8)
    run_jump_test(func, 8, 2, [2, 7, 2])

def test_jump_extended_args_unpack_ex_simple():
    def func(output):
        output.append(1)
        _, *_, _ = output.append(2) or "Spam"
        output.append(3)
    run_jump_test(func, 2, 3, [1, 3])

def test_jump_or_pop():
    def func(output):
        output.append(1)
        _ = output.append(2) and "Spam"
        output.append(3)
    run_jump_test(func, 2, 3, [1, 3])


# ---------------------------------------------------------------------------
# TestExtendedArgs tests
# ---------------------------------------------------------------------------

def test_extended_args_trace_unpack_long_sequence():
    ns = {}
    code = "def f():\n  (" + "y,\n   "*300 + ") = range(300)"
    exec(code, ns)
    f = ns["f"]
    for _ in range(20):
        f()
    counts = {"call": 0, "line": 0, "return": 0}
    def trace(frame, event, arg):
        counts[event] = counts.get(event, 0) + 1
        return trace
    sys.settrace(trace)
    f()
    sys.settrace(None)
    assert counts == {'call': 1, 'line': 301, 'return': 1}


# ---------------------------------------------------------------------------
# TestEdgeCases tests
# ---------------------------------------------------------------------------

def test_edge_same_object():
    def foo(*args):
        pass
    sys.settrace(foo)
    del foo
    sys.settrace(sys.gettrace())
    sys.settrace(None)
