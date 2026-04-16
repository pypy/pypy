import pytest

def _lineno_after_raise(f, *expected):
    try:
        f()
    except Exception as ex:
        t = ex.__traceback__
    else:
        assert False, "No exception raised"
    lines = []
    t = t.tb_next  # skip _lineno_after_raise frame
    while t:
        frame = t.tb_frame
        lines.append(
            None if frame.f_lineno is None else
            frame.f_lineno - frame.f_code.co_firstlineno
        )
        t = t.tb_next
    assert tuple(lines) == expected

def test_lineno_in_named_except():
    # PEP 626: traceback lineno should point at the re-raise inside except,
    # not at the implicit cleanup code generated for "except X as name"
    def in_named_except():
        try:
            1/0
        except Exception as ex:
            1/0
            pass
    _lineno_after_raise(in_named_except, 4)

def test_lineno_after_with():
    # PEP 626: traceback lineno after a with block should point at the line
    # after the with suite, not at the implicit __exit__ call
    class Noop:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    def after_with():
        with Noop():
            1/0
            pass
    _lineno_after_raise(after_with, 2)

def test_yield_in_nested_try_excepts():
    #Issue #25612
    class MainError(Exception):
        pass

    class SubError(Exception):
        pass

    def main():
        try:
            raise MainError()
        except MainError:
            try:
                yield
            except SubError:
                pass
            raise

    coro = main()
    coro.send(None)
    with pytest.raises(MainError):
        coro.throw(SubError())

def test_generator_doesnt_retain_old_exc2():
    # Issue bpo 28884#msg282532
    # Fixed in CPython via https://github.com/python/cpython/pull/1773
    import sys
    def g():
        try:
            raise ValueError
        except ValueError:
            yield 1
        assert sys.exc_info() == (None, None, None)
        yield 2

    gen = g()

    try:
        raise IndexError
    except IndexError:
        assert next(gen) == 1
    assert next(gen) == 2

def test_raise_in_generator():
    #Issue 25612#msg304117
    def g():
        yield 1
        raise
        yield 2

    with pytest.raises(ZeroDivisionError):
        i = g()
        try:
            1/0
        except:
            next(i)
            next(i)

def test_with_break_exit_raises():
    # sync with whose __exit__ raises, body exits via break.
    # The exception from __exit__ should propagate; __exit__ must not be called twice.
    called = []
    class CM:
        def __enter__(self): return self
        def __exit__(self, *e):
            called.append(1)
            raise ValueError("exit raised")

    def foo():
        for i in range(2):
            with CM():
                break

    try:
        foo()
        assert False, "expected ValueError"
    except ValueError as e:
        assert str(e) == "exit raised"
    assert called == [1], "expected __exit__ called exactly once, got %r" % called

def test_with_try_except_reraise():
    # 'with' block containing try/except that catches one exception and raises
    # another -- __exit__ must receive the new exception, not an internal wrapper.
    # Root cause: SETUP_WITH FinallyBlock survives into the with-exception handler;
    # RERAISE inside the handler re-enters via old block-stack mode with
    # SApplicationException instead of propagating out of the frame.
    # Fixed by Phase 6 (SETUP_WITH stops pushing FinallyBlock).
    class CM:
        def __enter__(self): pass
        def __exit__(self, *a): pass

    try:
        with CM():
            try:
                raise ImportError("original")
            except ImportError as e:
                raise ValueError(str(e))
    except ValueError:
        pass  # expected: ValueError propagates through __exit__ correctly
    # if TypeError raised instead, the bug is present (SApplicationException leaked)

def test_assertion_error_global_ignored():
    if hasattr(pytest, 'py3k_skip'):
        pytest.py3k_skip('only untranslated')
    global AssertionError

    class Foo(Exception):
        pass
    OrigAssertionError = AssertionError
    AssertionError = Foo
    try:
        with pytest.raises(OrigAssertionError): # not Foo!
            exec("assert 0") # to stop the pytest ast rewriting from touching it
    finally:
        AssertionError = OrigAssertionError
