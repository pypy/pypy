"""
Bytecode inspection for exception table Phase 7 work.
Run with:
  ~/oss/pypy2.7-v7.3.20-linux64/bin/pypy pytest.py pypy/interpreter/test/apptest_exctable_dis.py -s -v > /tmp/dis_pypy.txt 2>&1 &
Compare against CPython:
  python3.11 pytest.py -D pypy/interpreter/test/apptest_exctable_dis.py -s -v > /tmp/dis_cpython.txt 2>&1 &
"""
import dis


def _try_except_as():
    try:
        x = 1
    except ValueError as e:
        pass


def _try_except_no_name():
    try:
        x = 1
    except ValueError:
        pass


def _try_except_multi_handler():
    try:
        x = 1
    except TypeError as e:
        pass
    except ValueError as e:
        pass


def _try_finally():
    try:
        x = 1
    finally:
        pass


def _nested_try_except_in_except():
    try:
        x = 1
    except OSError:
        try:
            y = 2
        except ValueError:
            pass


def test_dis_try_except_as():
    print()
    print("=== try/except T as name ===")
    dis.dis(_try_except_as)


def test_dis_try_except_no_name():
    print()
    print("=== try/except T (no name) ===")
    dis.dis(_try_except_no_name)


def test_dis_try_except_multi():
    print()
    print("=== try/except with two handlers (both as name) ===")
    dis.dis(_try_except_multi_handler)


def _try_finally_inner():
    x = 1

def test_dis_try_finally():
    print()
    print("=== try/finally ===")
    dis.dis(_try_finally)
    print()
    print("=== plain function (no try) ===")
    dis.dis(_try_finally_inner)


def test_dis_nested():
    print()
    print("=== nested try/except inside except handler ===")
    dis.dis(_nested_try_except_in_except)


def _try_in_try():
    try:
        try:
            pass
        except Exception as ex:
            pass
    except Exception:
        pass


def test_dis_try_in_try():
    print()
    print("=== nested try-in-try (settrace lineno test) ===")
    dis.dis(_try_in_try)


def _try_finally_with_in_body():
    # try/finally where the finally body contains a 'with' statement.
    # Regression: assemble.py used to emit a spurious exception table entry
    # that extended the outer handler into the finally body, causing the
    # inner with-block's handler to be bypassed at runtime.
    log = []

    class CM:
        def __enter__(self):
            log.append('enter')
            return self
        def __exit__(self, *a):
            log.append(('exit', bool(a[0])))
            return True  # suppress any exception from within the with block

    try:
        log.append('try')
    finally:
        with CM():
            log.append('in with')

    return log


def test_try_finally_with_in_body():
    log = _try_finally_with_in_body()
    assert log == ['try', 'enter', 'in with', ('exit', False)], log


def _try_finally_with_raises_in_body(exc_class):
    # Variant: with-block inside finally raises; must be handled by the
    # with-block's __exit__, not by the outer exception-path handler.
    log = []

    class CM:
        def __enter__(self):
            return self
        def __exit__(self, tp, val, tb):
            log.append(('exit', tp is exc_class))
            return True  # suppress

    try:
        pass
    finally:
        with CM():
            raise exc_class("inside with")

    return log


def test_try_finally_with_raises_in_body():
    log = _try_finally_with_raises_in_body(ValueError)
    assert log == [('exit', True)], log


def _except_star_all_caught():
    try:
        raise KeyError
    except* Exception as e:
        pass


def test_except_star_cleanup_lineno():
    # GH-101517 / pdb test: after the except* body runs, the RETURN_VALUE for
    # the "all exceptions caught" path must be attributed to the except* clause
    # line, not to the body line.  pdb relies on this to display the right line.
    import sys

    print()
    print("=== except* cleanup lineno dis ===")
    dis.dis(_except_star_all_caught)

    events = []
    base = _except_star_all_caught.__code__.co_firstlineno

    def tracer(frame, event, arg):
        if frame.f_code is _except_star_all_caught.__code__:
            events.append((event, frame.f_lineno - base + 1))
        return tracer

    sys.settrace(tracer)
    _except_star_all_caught()
    sys.settrace(None)

    print("trace events (relative line):", events)
    return_linenos = [ln for evt, ln in events if evt == 'return']
    # except* clause is relative line 4; body (pass) is relative line 5.
    # CPython fires the return event at line 4 (the except* clause).
    assert return_linenos == [4], (
        "expected return event at except* clause (line 4), got: {}".format(return_linenos)
    )
