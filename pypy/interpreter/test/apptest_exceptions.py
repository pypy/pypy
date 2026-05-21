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

def test_lineno_reraise_through_finally():
    # Exception propagating through a try/finally should report the lineno of
    # the finally cleanup code (matching CPython), not the implicit RERAISE.
    def func():
        try:
            raise ValueError("x")
        finally:
            pass
    _lineno_after_raise(func, 4)

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


def test_sys_exc_info_restore_direct():
    import sys
    assert sys.exc_info() == (None, None, None)
    try:
        raise KeyError('foo')
    except KeyError:
        pass
    assert sys.exc_info() == (None, None, None), sys.exc_info()

def test_sys_exc_info_restore_nested():
    import sys
    assert sys.exc_info() == (None, None, None)
    def inner():
        try:
            raise KeyError('foo')
        except KeyError:
            pass
    inner()
    assert sys.exc_info() == (None, None, None), sys.exc_info()


def test_sys_exc_info_restore_class_body():
    import sys
    assert sys.exc_info() == (None, None, None)
    class Foo:
        try:
            raise KeyError('foo')
        except KeyError:
            pass
    assert sys.exc_info() == (None, None, None), sys.exc_info()

def test_sys_exc_info_restore_reraise_caught():
    import sys
    assert sys.exc_info() == (None, None, None)
    def inner():
        try:
            raise ValueError('outer')
        except ValueError:
            try:
                raise KeyError('inner')
            except KeyError:
                pass
    inner()
    assert sys.exc_info() == (None, None, None), sys.exc_info()

def test_sys_exc_info_finally_reraise():
    import sys
    assert sys.exc_info() == (None, None, None)
    def inner():
        try:
            try:
                raise KeyError('a')
            finally:
                pass
        except KeyError:
            pass
    inner()
    assert sys.exc_info() == (None, None, None), sys.exc_info()

def test_sys_exc_info_finally_nested():
    import sys
    assert sys.exc_info() == (None, None, None)
    def inner():
        try:
            try:
                raise KeyError('a')
            except KeyError:
                raise ValueError('b')
        except ValueError:
            pass
    inner()
    assert sys.exc_info() == (None, None, None), sys.exc_info()

def test_sys_exc_info_finally_nested_as_name():
    import sys
    assert sys.exc_info() == (None, None, None)
    def inner():
        try:
            try:
                raise KeyError('a')
            except KeyError as k:
                raise ValueError('b')
        except ValueError:
            pass
    inner()
    assert sys.exc_info() == (None, None, None), sys.exc_info()

def test_exception_trivial():
    def f():
        try:
            raise Exception()
        except Exception as e:
            return 1
        return 2
    assert f() == 1


def test_exception_as_name():
    def f():
        try:
            raise Exception(1)
        except Exception as e:
            return e.args[0]
    assert f() == 1


def test_finally_return():
    def f(a):
        try:
            if a:
                raise Exception
            a = -12
        finally:
            return a
    assert f(0) == -12
    assert f(1) == 1


def test_raise_non_exception():
    try:
        raise 1
    except TypeError as e:
        assert "exceptions must derive from BaseException" in str(e)
    else:
        assert False, "expected TypeError"


def test_nested_except_raise_stored():
    # CPython 3.11 exception table for this pattern:
    #   try body -> outer_handler
    #   inner try body -> inner_handler
    #   inner handler check+STORE -> inner outer_cleanup
    #   inner handler body (incl RAISE_VARARGS) -> inner cleanup_end
    #   inner cleanup_end -> inner outer_cleanup
    #   outer handler check -> outer outer_cleanup
    import dis
    def f():
        try:
            z = 0
            try:
                "x" + 1
            except TypeError as e:
                z = 5
                raise e
        except TypeError:
            return z
    print()
    dis.dis(f)
    assert f() == 5


def test_except_zero_division():
    def f(v):
        z = 0
        try:
            z = 1 // v
        except ZeroDivisionError as e:
            z = "infinite result"
        return z
    assert f(2) == 0
    assert f(0) == "infinite result"
    try:
        f('x')
    except TypeError as e:
        assert "unsupported operand type" in str(e)
    else:
        assert False, "expected TypeError"


def test_try_finally_break():
    def f(n):
        total = 0
        for i in range(n):
            try:
                if i == 4:
                    break
            finally:
                total += i
        return total
    assert f(4) == 1+2+3
    assert f(9) == 1+2+3+4


def test_try_finally_continue():
    def f(n):
        total = 0
        for i in range(n):
            try:
                if i == 4:
                    continue
            finally:
                total += 100
            total += i
        return total
    assert f(4) == 1+2+3+400
    assert f(9) == 1+2+3 + 5+6+7+8+900


def test_try_except_finally_nested():
    import dis
    def run():
        x = 5
        try:
            try:
                if x > 2:
                    raise ValueError
            finally:
                x += 1
        except ValueError:
            x *= 7
        return x
    print()
    dis.dis(run)
    assert run() == 42


def test_sys_exc_info_with_propagates():
    # Regression: a with-statement whose __exit__ returns falsy must not
    # leak sys.exc_info when the body raises and the outer frame catches.
    # The exception-table entry for the with-cleanup block must cover the
    # RERAISE 2 instruction so the outer_cleanup (COPY 3; POP_EXCEPT;
    # RERAISE 1) runs and restores sys.exc_info before re-raising.
    import sys
    assert sys.exc_info() == (None, None, None)
    class CM:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False  # propagate
    def inner():
        try:
            with CM():
                raise ImportError("boom")
        except ImportError:
            pass
    inner()
    assert sys.exc_info() == (None, None, None), sys.exc_info()
