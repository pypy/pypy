import sys, dis
from pytest import raises


def test_with_try_except_as_reraise():
    """with + try/except T as name where the handler raises: the new exception
    must propagate through the with block's __exit__ without crashing.
    Mirrors import_helper.import_module: with CM(): try: ... except E as msg: raise Other"""
    class CM:
        def __init__(self): self.exited = False; self.exc_type = None
        def __enter__(self): return self
        def __exit__(self, tp, val, tb):
            self.exited = True
            self.exc_type = tp
            return False  # do not suppress

    cm = CM()

    # normal_return=True exercises the normal-exit path so POP_BLOCK fires,
    # mirroring import_helper.import_module which also has a normal return.
    def inner(cm, raise_in_handler):
        with cm:
            try:
                if raise_in_handler:
                    raise ValueError("original")
                return "ok"
            except ValueError as e:
                raise TypeError("new")

    print("=== dis(inner) ===")
    dis.dis(inner)
    # Normal path should work
    assert inner(cm, False) == "ok"
    # Exception path: TypeError must propagate through __exit__
    try:
        inner(cm, True)
    except TypeError:
        pass
    assert cm.exited, "__exit__ was not called"
    assert cm.exc_type is TypeError, "wrong exc type to __exit__: %r" % cm.exc_type

def test_simple():
    try:
        raise TypeError()
    except* TypeError:
        a = 1
    except* ValueError:
        a = 2
    assert a == 1

def test_both_excepts_run():
    l = []
    try:
        raise ExceptionGroup('abc', [ValueError(), TypeError()])
    except* TypeError:
        l.append(1)
    except* ValueError:
        l.append(2)
    print(l)
    assert l == [1, 2]

def raises_one():
    try:
        raise ExceptionGroup('abc', [ValueError(), TypeError()])
    except* TypeError:
        pass

def test_reraise():
    a = 1
    try:
        raises_one()
    except* ValueError:
        a = 0
    assert a == 0 # and in particular, we reach this line

def error_in_handler():
    try:
        raise ExceptionGroup('abc', [ValueError(), TypeError()])
    except* TypeError:
        1 / 0

def test_error_in_exception_handler():
    a = 1
    try:
        error_in_handler()
    except ExceptionGroup as e:
        assert repr(e) == "ExceptionGroup('', [ZeroDivisionError('division by zero'), ExceptionGroup('abc', [ValueError()])])"
        # TODO what's wrong with the context?
        #assert repr(e.exceptions[0].__context__) == "ExceptionGroup('abc', [TypeError()])"
    else:
        assert 0, "an ExceptionGroup should be raised"

def test_name_except_star():
    l = []
    value = ValueError()
    typ = TypeError()
    try:
        raise ExceptionGroup('abc', [value, typ])
    except* TypeError as e1:
        assert e1.exceptions[0] is typ
        l.append(1)
    except* ValueError as e2:
        assert e2.exceptions[0] is value
        l.append(2)
    print(l)
    assert l == [1, 2]
    with raises(UnboundLocalError):
        e1
    with raises(UnboundLocalError):
        e2

def test_try_star_name_raise_in_except_handler():
    l = []
    value = ValueError()
    typ = TypeError()
    try:
        try:
            raise ExceptionGroup('abc', [value, typ])
        except* TypeError as e1:
            1 / 0
    except Exception as e:
        assert "ZeroDivisionError" in repr(e)
    with raises(UnboundLocalError):
        e1

def maybe_raise_typeerror(x):
    if x:
        raise TypeError

def try_except_star_with_else(x):
    try:
        maybe_raise_typeerror(x)
    except* TypeError:
        a = 1
    else:
        a = 2
    return a

def test_try_except_star_with_else():
    assert try_except_star_with_else(True) == 1
    assert try_except_star_with_else(False) == 2

def test_return_break_continue_in_except_group_handler():
    for kw in "return break continue".split():
        src = f"""\
def try_except_star_with_else_direct_return(x):
    try:
        pass
    except* TypeError:
        {kw}
    """
        with raises(SyntaxError) as info:
            exec(src)
        assert "cannot appear in an except* block" in str(info.value)

def test_return_in_except_star_outside_function():
    src = """\
try:
    pass
except* TypeError:
    return
    """
    with raises(SyntaxError) as info:
        exec(src)
    # CPython 3.11 reports "'return' outside function" (that error takes priority)
    assert "return" in str(info.value)

def test_syntax_error_both_except_except_star():
    src = """\
try:
    pass
except ValueError:
    pass
except* TypeError:
    pass
"""
    with raises(SyntaxError) as info:
        exec(src)
    assert str(info.value).startswith("cannot have both 'except' and 'except*' on the same 'try'")


def maybe_raise(err):
    if err:
        raise err
    

def with_finally(l, err):
    try:
        maybe_raise(err)
    except* TypeError:
        l.append(1)
    except* ValueError:
        l.append(2)
    else:
        l.append(3)
    finally:
        l.append(4)

def test_finally():
    l = []
    with_finally(l, None)
    assert l == [3, 4]
    l = []
    with_finally(l, ValueError())
    assert l == [2, 4]
    l = []
    with_finally(l, TypeError())
    assert l == [1, 4]
    l = []
    with_finally(l, ExceptionGroup('abc', [ValueError(), TypeError()]))
    assert l == [1, 2, 4]
    with raises(ZeroDivisionError):
        l = []
        with_finally(l, ZeroDivisionError())
    assert l == [4]

def test_invalid_catching_class():
    for cls, eg in [(int, False), (ExceptionGroup, True), (BaseExceptionGroup, True), ((ValueError, ExceptionGroup), True), ((int, ), False)]:
        with raises(TypeError) as info:
            try:
                1/0
            except* cls:
                pass
        if eg:
            assert "catching ExceptionGroup with except* is not allowed. Use except instead." in str(info.value)
        else:
            assert "catching classes that do not inherit from BaseException is not allowed" in str(info.value)
        assert isinstance(info.value.__context__, ZeroDivisionError)

def test_exceptiongroup_is_generic():
    assert isinstance(ExceptionGroup[int], type(list[int]))
    assert isinstance(BaseExceptionGroup[int], type(list[int]))

def test_split_does_not_copy_non_sequence_notes():
    # __notes__ should be a sequence, which is shallow copied.
    # If it is not a sequence, the split parts don't get any notes.
    eg = ExceptionGroup("eg", [ValueError(1), TypeError(2)])
    eg.__notes__ = 123
    match, rest = eg.split(TypeError)
    assert not hasattr(match, '__notes__')
    assert not hasattr(rest, '__notes__')


def assert_exception_is_like(exc, template):
    if exc is None and template is None:
        return

    assert template is not None
    assert exc is not None

    if not isinstance(exc, ExceptionGroup):
        assert exc.__class__ == template.__class__
        assert exc.args[0] == template.args[0]
    else:
        assert exc.message == template.message
        assert len(exc.exceptions) == len(template.exceptions)
        for e, t in zip(exc.exceptions, template.exceptions):
            assert_exception_is_like(e, t)


def do_split_test_named(exc, T, match_template, rest_template):
    initial_sys_exception = sys.exc_info()[1]
    sys_exception = match = rest = None
    try:
        try:
            raise exc
        except* T as e:
            sys_exception = sys.exc_info()[1]
            match = e
    except BaseException as e:
        rest = e

    assert sys_exception == match
    assert_exception_is_like(match, match_template)
    assert_exception_is_like(rest, rest_template)
    assert sys.exc_info()[1] == initial_sys_exception
do_split_test = do_split_test_named

def test_exception_group_except_star_Exception_not_wrapped():
    do_split_test(
        ExceptionGroup("eg", [ValueError("V")]),
        Exception,
        ExceptionGroup("eg", [ValueError("V")]),
        None)

def test_match_single_type_partial_match():
    do_split_test(
        ExceptionGroup(
            "test3",
            [ValueError("V1"), OSError("OS"), ValueError("V2")]),
        ValueError,
        ExceptionGroup("test3", [ValueError("V1"), ValueError("V2")]),
        ExceptionGroup("test3", [OSError("OS")]))

def test_reraise_plain_exception_named():
    try:
        try:
            raise ValueError(42)
        except* ValueError as e:
            print('sys.exc_info', sys.exc_info())
            print('except* e', e)
            raise e
    except ExceptionGroup as e:
        print('ExceptionGroup', e)
        exc = e

    assert_exception_is_like(
        exc, ExceptionGroup("", [ValueError(42)]))

def except_type(eg, type):
    match, rest = None, None
    try:
        try:
            raise eg
        except* type  as e:
            match = e
    except Exception as e:
        rest = e
    return match, rest

def test_unhashable():
    class UnhashableExc(ValueError):
        __hash__ = None

    eg = ExceptionGroup("eg", [TypeError(1), UnhashableExc(2)])
    match, rest = except_type(eg, UnhashableExc)
    assert_exception_is_like(
        match, ExceptionGroup("eg", [UnhashableExc(2)]))
    assert_exception_is_like(
        rest, ExceptionGroup("eg", [TypeError(1)]))

def test_broken_eq():
    class Bad(ValueError):
        def __eq__(self, other):
            raise RuntimeError()

    eg = ExceptionGroup("eg", [TypeError(1), Bad(2)])
    match, rest = except_type(eg, TypeError)
    assert_exception_is_like(
        match, ExceptionGroup("eg", [TypeError(1)]))
    assert_exception_is_like(
        rest, ExceptionGroup("eg", [Bad(2)]))

def _except_star_clause_line(func):
    """Return the line number of the except* clause in func via CHECK_EG_MATCH."""
    instrs = list(dis.get_instructions(func))
    check_eg = [i for i in instrs if i.opname == 'CHECK_EG_MATCH']
    assert check_eg, "no CHECK_EG_MATCH found in %r" % func
    return check_eg[0].positions.lineno

def test_except_star_cleanup_lineno():
    """Cleanup opcodes (LIST_APPEND) after except* must not be attributed to a
    line before the except* clause (e.g. co_firstlineno of the function) — that
    would misreport where the cleanup runs."""
    def func():
        try:
            raise KeyError
        except* Exception as e:
            pass

    except_star_line = _except_star_clause_line(func)
    instrs = list(dis.get_instructions(func))
    la1 = [i for i in instrs if i.opname == 'LIST_APPEND' and i.arg == 1]
    assert la1, "no LIST_APPEND 1 found"
    for i in la1:
        if i.positions is not None and i.positions.lineno is not None:
            assert i.positions.lineno >= except_star_line, (
                "LIST_APPEND 1 lineno=%r is before except* clause line %r" %
                (i.positions.lineno, except_star_line))

def test_traceback_frames_preserved_through_except_star():
    # When an exception raised inside except* propagates through call frames,
    # all intermediate frames must appear in the traceback.
    import traceback

    def inner():
        try:
            raise ExceptionGroup("group", [ValueError(1)])
        except* ValueError:
            raise ValueError(2)

    def outer():
        try:
            raise ExceptionGroup("group", [TypeError(1)])
        except* TypeError:
            inner()

    try:
        outer()
    except ValueError as e:
        tb_frames = [frame.f_code.co_name for frame, _ in traceback.walk_tb(e.__traceback__)]

    # must include both outer() and inner(), not just the outermost frame
    assert 'inner' in tb_frames, "inner() missing from traceback: %r" % tb_frames
    assert 'outer' in tb_frames, "outer() missing from traceback: %r" % tb_frames


def test_except_star_trace_return_lineno():
    """The 'return' trace event after an except* block should report the except*
    clause line, not co_firstlineno (which was the wrong pre-fix behaviour)."""
    events = []

    def tracer(frame, event, arg):
        if frame.f_code.co_name == 'func':
            events.append((event, frame.f_lineno))
        return tracer

    def func():
        try:
            raise KeyError
        except* Exception as e:
            pass

    except_star_line = _except_star_clause_line(func)

    sys.settrace(tracer)
    try:
        func()
    finally:
        sys.settrace(None)

    ret_events = [lineno for event, lineno in events if event == 'return']
    assert ret_events, "no return event recorded"
    assert ret_events[-1] >= except_star_line, (
        "return event at line %d, expected >= except* clause line %d "
        "(cleanup must not report a line before the except* block)" %
        (ret_events[-1], except_star_line))


# ---------------------------------------------------------------------------
# Bug 1: async for inside async with -- StopAsyncIteration bypasses ExceptBlock
# ---------------------------------------------------------------------------

def _run_coro(coro):
    """Drive a coroutine to completion without asyncio."""
    try:
        coro.send(None)
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


def test_async_for_inside_async_with_exits_once():
    """StopAsyncIteration that ends an async for loop must not be delivered
    to the enclosing async with's __aexit__.  Before the fix, handle_operation_error
    found the async-with's exception table entry instead of routing through the
    ExceptBlock pushed by SETUP_EXCEPT for the async iterator, so __aexit__ was
    called with StopAsyncIteration and then called a second time on normal exit."""
    exit_calls = []

    class ACM:
        async def __aenter__(self):
            return self
        async def __aexit__(self, tp, val, tb):
            exit_calls.append(tp)
            return False

    class AIter:
        def __init__(self, n):
            self.i = 0
            self.n = n
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self.i >= self.n:
                raise StopAsyncIteration
            self.i += 1
            return self.i

    async def main():
        async with ACM():
            async for _ in AIter(3):
                pass

    _run_coro(main())
    assert exit_calls == [None], \
        "__aexit__ call list wrong: %r (expected [None])" % exit_calls


# ---------------------------------------------------------------------------
# Bug 2: SApplicationException leaking out of try/finally inside a generator.
# When an exception is raised inside a try/finally body that contains a with
# statement (even if the with block is never entered), the exception must
# propagate through the finally block and be caught by the enclosing except.

def test_generator_exception_in_enter():
    """The exception is raised inside __enter__ (after the
    CM expression succeeds)."""
    log = []

    class CM:
        def __enter__(self):
            log.append(('enter'))
            raise OSError("enter failed")
            return self

        def __exit__(self, tp, val, tb):
            log.append(('exit'))
            return False

        def __iter__(self):
            log.append(('exit'))
            return self

        def __next__(self):
            raise OSError("enter failed")
        

    def gen(dummy):
        try:
            try:
                with CM() as it:
                    for x in it:
                        yield x
            except OSError:
                raise
            finally:
                if not dummy:
                    log.append('finally')
        except OSError:
            log.append('caught')
            return

    if 0:
        import dis
        print("========= gen ============ ")
        print(dis.dis(gen))
        print("========= gen ============ ")
    list(gen(True))
    assert log == ['enter', 'caught'], "log=%r" % log
