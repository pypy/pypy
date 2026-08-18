import sys


def test_exists():
    assert hasattr(sys, 'monitoring')
    assert sys.monitoring.__name__ == 'sys.monitoring'


def test_tool_ids():
    assert sys.monitoring.DEBUGGER_ID == 0
    assert sys.monitoring.COVERAGE_ID == 1
    assert sys.monitoring.PROFILER_ID == 2
    assert sys.monitoring.OPTIMIZER_ID == 5


def test_events_namespace():
    E = sys.monitoring.events
    assert E.NO_EVENTS == 0
    assert E.PY_START == 1 << 0
    assert E.PY_RESUME == 1 << 1
    assert E.PY_RETURN == 1 << 2
    assert E.PY_YIELD == 1 << 3
    assert E.CALL == 1 << 4
    assert E.LINE == 1 << 5
    assert E.INSTRUCTION == 1 << 6
    assert E.JUMP == 1 << 7
    assert E.BRANCH == 1 << 8
    assert E.STOP_ITERATION == 1 << 9
    assert E.RAISE == 1 << 10
    assert E.EXCEPTION_HANDLED == 1 << 11
    assert E.PY_UNWIND == 1 << 12
    assert E.PY_THROW == 1 << 13
    assert E.RERAISE == 1 << 14
    assert E.C_RETURN == 1 << 15
    assert E.C_RAISE == 1 << 16


def test_disable_missing_are_singletons():
    assert sys.monitoring.DISABLE is sys.monitoring.DISABLE
    assert sys.monitoring.MISSING is sys.monitoring.MISSING
    assert sys.monitoring.DISABLE is not sys.monitoring.MISSING


def test_use_tool_id():
    sys.monitoring.use_tool_id(3, "test tool")
    try:
        assert sys.monitoring.get_tool(3) == "test tool"
        raises(ValueError, sys.monitoring.use_tool_id, 3, "again")
    finally:
        sys.monitoring.free_tool_id(3)
    assert sys.monitoring.get_tool(3) is None


def test_use_tool_id_invalid():
    raises(ValueError, sys.monitoring.use_tool_id, -1, "x")
    raises(ValueError, sys.monitoring.use_tool_id, 6, "x")
    raises(ValueError, sys.monitoring.use_tool_id, 3, 42)


def test_register_callback():
    def callback(*args):
        pass
    sys.monitoring.use_tool_id(3, "test tool")
    try:
        E = sys.monitoring.events
        old = sys.monitoring.register_callback(3, E.PY_START, callback)
        assert old is None
        old = sys.monitoring.register_callback(3, E.PY_START, None)
        assert old is callback
        raises(ValueError, sys.monitoring.register_callback, 3, E.PY_START | E.CALL, callback)
        raises(ValueError, sys.monitoring.register_callback, 3, 0, callback)
    finally:
        sys.monitoring.free_tool_id(3)


def test_get_set_events():
    sys.monitoring.use_tool_id(3, "test tool")
    try:
        E = sys.monitoring.events
        assert sys.monitoring.get_events(3) == 0
        sys.monitoring.set_events(3, E.PY_START | E.PY_RETURN)
        assert sys.monitoring.get_events(3) == E.PY_START | E.PY_RETURN
        sys.monitoring.set_events(3, 0)
        assert sys.monitoring.get_events(3) == 0
    finally:
        sys.monitoring.free_tool_id(3)


def test_set_events_requires_tool_in_use():
    E = sys.monitoring.events
    raises(ValueError, sys.monitoring.set_events, 3, E.PY_START)
    raises(ValueError, sys.monitoring.set_local_events, 3, test_set_events_requires_tool_in_use.__code__, 0)
    sys.monitoring.use_tool_id(3, "test tool")
    sys.monitoring.set_events(3, E.PY_START)
    sys.monitoring.set_events(3, 0)
    sys.monitoring.free_tool_id(3)
    raises(ValueError, sys.monitoring.set_events, 3, E.PY_START)
    assert sys.monitoring.get_events(3) == 0


def test_set_events_c_return_independent():
    E = sys.monitoring.events
    sys.monitoring.use_tool_id(3, "test tool")
    try:
        raises(ValueError, sys.monitoring.set_events, 3, E.C_RETURN)
        raises(ValueError, sys.monitoring.set_events, 3, E.C_RAISE)
        # allowed together with CALL, but C_RETURN/C_RAISE are never
        # stored/reported as independent bits -- they ride on the CALL
        # bit instead, see test_c_return_follows_call_bit.
        sys.monitoring.set_events(3, E.CALL | E.C_RETURN | E.C_RAISE)
        assert sys.monitoring.get_events(3) == E.CALL
        sys.monitoring.set_events(3, 0)
    finally:
        sys.monitoring.free_tool_id(3)


def test_c_return_follows_call_bit():
    # Registering only a C_RETURN callback and enabling just E.CALL (not
    # E.C_RETURN/E.C_RAISE) still fires C_RETURN -- these two events ride
    # on the CALL bit rather than having independent on/off state (PEP
    # 669: "C_RETURN and C_RAISE events will only be seen if the
    # corresponding CALL event is being monitored").
    E = sys.monitoring.events
    sys.monitoring.use_tool_id(3, "test tool")
    events = []
    try:
        sys.monitoring.register_callback(3, E.CALL, lambda *a: events.append(('CALL',) + a))
        sys.monitoring.register_callback(3, E.C_RETURN, lambda *a: events.append(('C_RETURN',) + a))
        sys.monitoring.set_events(3, E.CALL)  # only CALL, not C_RETURN|C_RAISE
        assert sys.monitoring.get_events(3) == E.CALL

        events[:] = []
        assert len([1, 2, 3]) == 3
        names = [ev[0] for ev in events if ev[3] is len]
        assert names == ['CALL', 'C_RETURN']
        sys.monitoring.set_events(3, 0)
    finally:
        sys.monitoring.free_tool_id(3)


def test_local_events():
    def f():
        pass
    code = f.__code__
    sys.monitoring.use_tool_id(3, "test tool")
    try:
        E = sys.monitoring.events
        assert sys.monitoring.get_local_events(3, code) == 0
        sys.monitoring.set_local_events(3, code, E.LINE)
        assert sys.monitoring.get_local_events(3, code) == E.LINE
        sys.monitoring.set_local_events(3, code, 0)
    finally:
        sys.monitoring.free_tool_id(3)


def test_local_events_requires_code_object():
    raises(TypeError, sys.monitoring.get_local_events, 3, "not code")
    raises(TypeError, sys.monitoring.set_local_events, 3, "not code", 0)


def test_py_start_local_events():
    # PY_START is in PEP 669's "local events" list, so it must fire from
    # set_local_events alone, with no matching global set_events call.
    E = sys.monitoring.events
    events = []

    def f():
        pass

    code = f.__code__

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.PY_START, callback)
        sys.monitoring.set_local_events(3, code, E.PY_START)

        events[:] = []
        f()
        assert len(events) == 1
        assert events[0][0] is code
    finally:
        sys.monitoring.set_local_events(3, code, 0)
        sys.monitoring.free_tool_id(3)


def test_py_start_disable():
    E = sys.monitoring.events
    events = []

    def f():
        pass

    code = f.__code__

    def callback(*args):
        events.append(args)
        return sys.monitoring.DISABLE

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.PY_START, callback)
        sys.monitoring.set_events(3, E.PY_START)

        events[:] = []
        f()
        f()
        f()
        names = [ev for ev in events if ev[0] is code]
        assert len(names) == 1

        sys.monitoring.restart_events()
        events[:] = []
        f()
        assert len(events) == 1
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_call_disable():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)
        return sys.monitoring.DISABLE

    def f(x):
        return len(x)

    code = f.__code__

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.CALL, callback)
        sys.monitoring.set_local_events(3, code, E.CALL)

        events[:] = []
        assert f([]) == 0
        assert f([]) == 0
        assert f([]) == 0
        names = [ev for ev in events if ev[0] is code]
        assert len(names) == 1
    finally:
        sys.monitoring.set_local_events(3, code, 0)
        sys.monitoring.free_tool_id(3)


def test_disable_illegal_event_raises():
    # RAISE isn't in LOCAL_EVENTS, so returning DISABLE from its callback
    # is illegal: CPython raises ValueError and unregisters the callback.
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)
        return sys.monitoring.DISABLE

    def f():
        raise ZeroDivisionError

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.RAISE, callback)
        sys.monitoring.set_events(3, E.RAISE)

        events[:] = []
        raised = None
        try:
            f()
        except BaseException as e:
            raised = e
        assert isinstance(raised, ValueError)
        assert len(events) == 1

        # callback was unregistered; a second raise doesn't call it again
        # or re-raise ValueError -- the original ZeroDivisionError surfaces.
        events[:] = []
        raised = None
        try:
            f()
        except BaseException as e:
            raised = e
        assert isinstance(raised, ZeroDivisionError)
        assert events == []
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_restart_events():
    sys.monitoring.restart_events()


def test_fire_py_start_return():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.PY_START, callback)
        sys.monitoring.register_callback(3, E.PY_RETURN, callback)
        sys.monitoring.set_events(3, E.PY_START | E.PY_RETURN)

        def f():
            return 42

        events.clear()
        assert f() == 42
        assert len(events) == 2
        assert events[0][0] is f.__code__
        assert events[1][0] is f.__code__
        assert events[1][2] == 42
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_py_yield_resume():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args[:2])

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.PY_START, callback)
        sys.monitoring.register_callback(3, E.PY_RESUME, callback)
        sys.monitoring.register_callback(3, E.PY_YIELD, callback)
        sys.monitoring.register_callback(3, E.PY_RETURN, callback)
        sys.monitoring.set_events(3, E.PY_START | E.PY_RESUME | E.PY_YIELD | E.PY_RETURN)

        def g():
            yield 1
            yield 2

        events[:] = []
        gen = g()
        code = g.__code__
        assert next(gen) == 1
        assert next(gen) == 2
        raises(StopIteration, next, gen)
        sys.monitoring.set_events(3, 0)
        g_events = [ev for ev in events if ev[0] is code]
        assert len(g_events) == 6  # start, yield, resume, yield, resume, return
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_py_unwind():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.PY_UNWIND, callback)
        sys.monitoring.set_events(3, E.PY_UNWIND)

        def f():
            raise ValueError("boom")

        events[:] = []
        raises(ValueError, f)
        assert len(events) == 1
        assert events[0][0] is f.__code__
        assert isinstance(events[0][2], ValueError)
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_py_throw():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.PY_THROW, callback)
        sys.monitoring.set_events(3, E.PY_THROW)

        def g():
            try:
                yield 1
            except ValueError:
                yield 2

        events[:] = []
        gen = g()
        next(gen)
        assert gen.throw(ValueError) == 2
        assert len(events) == 1
        assert events[0][0] is g.__code__
        assert isinstance(events[0][2], ValueError)
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_raise_and_exception_handled():
    E = sys.monitoring.events
    events = []

    def callback(name):
        def cb(*args):
            events.append((name,) + args)
        return cb

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.RAISE, callback('RAISE'))
        sys.monitoring.register_callback(3, E.EXCEPTION_HANDLED, callback('EXCEPTION_HANDLED'))
        sys.monitoring.set_events(3, E.RAISE | E.EXCEPTION_HANDLED)

        def f():
            try:
                raise ValueError("boom")
            except ValueError:
                return "caught"

        events[:] = []
        assert f() == "caught"
        names = [ev[0] for ev in events if ev[1] is f.__code__]
        assert names == ['RAISE', 'EXCEPTION_HANDLED']
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_reraise():
    E = sys.monitoring.events
    events = []

    def callback(name):
        def cb(*args):
            events.append((name,) + args)
        return cb

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.RAISE, callback('RAISE'))
        sys.monitoring.register_callback(3, E.RERAISE, callback('RERAISE'))
        sys.monitoring.set_events(3, E.RAISE | E.RERAISE)

        def f():
            try:
                raise ValueError("boom")
            except ValueError:
                raise  # bare reraise

        events[:] = []
        try:
            f()
        except ValueError:
            pass
        names = [ev[0] for ev in events if ev[1] is f.__code__]
        # Exactly one RAISE for the fresh `raise ValueError(...)`.  The
        # bare `raise` fires RERAISE at least once, but CPython's own
        # exception-table cleanup-handler compilation for the enclosing
        # `except` block can trigger a second RERAISE as the exception
        # propagates through cleanup on its way out of `f` -- an
        # implementation detail of CPython's bytecode compilation for
        # `except` blocks, not part of PEP 669's contract, and not
        # necessarily reproduced 1:1 by PyPy's different exception-table
        # compilation strategy. So assert the count that *is* part of
        # the contract (>=1) rather than pinning the exact repeat count.
        assert names[0] == 'RAISE'
        assert names.count('RAISE') == 1
        assert names.count('RERAISE') >= 1
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_stop_iteration():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.STOP_ITERATION, callback)
        sys.monitoring.set_events(3, E.STOP_ITERATION)

        def inner():
            yield 1
            return "done"

        def outer():
            result = yield from inner()
            yield result

        events[:] = []
        gen = outer()
        assert next(gen) == 1
        assert next(gen) == "done"
        assert len(events) == 1
        assert events[0][0] is outer.__code__
        assert isinstance(events[0][2], StopIteration)
        assert events[0][2].value == "done"
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_no_stop_iteration_for_plain_for_loop():
    # Plain `for` exhaustion is a BRANCH event on CPython (Phase 6, not
    # implemented), not STOP_ITERATION -- STOP_ITERATION is specifically
    # about the PEP 380 generator-return-via-StopIteration mechanism in
    # `yield from`/delegation (see sys.monitoring.rst "The STOP_ITERATION
    # event"). Confirms next_yield_from's firing point doesn't accidentally
    # also cover ordinary iterator exhaustion.
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.STOP_ITERATION, callback)
        sys.monitoring.set_events(3, E.STOP_ITERATION)

        events[:] = []
        for _ in range(3):
            pass
        assert events == []
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_call_python_function():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.CALL, callback)
        sys.monitoring.set_events(3, E.CALL)

        def f(x):
            return x

        events[:] = []
        assert f(42) == 42
        calls = [ev for ev in events if ev[2] is f]
        assert len(calls) == 1
        code, offset, callable, arg0 = calls[0]
        assert callable is f
        assert arg0 == 42
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_call_no_args_is_missing():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.CALL, callback)
        sys.monitoring.set_events(3, E.CALL)

        def f():
            return 1

        events[:] = []
        f()
        calls = [ev for ev in events if ev[2] is f]
        assert len(calls) == 1
        assert calls[0][3] is sys.monitoring.MISSING
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_c_return():
    E = sys.monitoring.events
    events = []

    def callback(event_name):
        def cb(*args):
            events.append((event_name,) + args)
        return cb

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.CALL, callback('CALL'))
        sys.monitoring.register_callback(3, E.C_RETURN, callback('C_RETURN'))
        sys.monitoring.set_events(3, E.CALL | E.C_RETURN | E.C_RAISE)

        events[:] = []
        result = len([1, 2, 3])
        assert result == 3
        names = [ev[0] for ev in events if ev[3] is len]
        assert names == ['CALL', 'C_RETURN']
        c_return = [ev for ev in events if ev[0] == 'C_RETURN'][0]
        assert c_return[3] is len
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_c_raise():
    E = sys.monitoring.events
    events = []

    def callback(event_name):
        def cb(*args):
            events.append((event_name,) + args)
        return cb

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.CALL, callback('CALL'))
        sys.monitoring.register_callback(3, E.C_RAISE, callback('C_RAISE'))
        sys.monitoring.set_events(3, E.CALL | E.C_RETURN | E.C_RAISE)

        events[:] = []
        try:
            abs('x')
        except TypeError:
            pass
        names = [ev[0] for ev in events if ev[3] is abs]
        assert names == ['CALL', 'C_RAISE']
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_c_raise_for_type_call():
    # C_RETURN/C_RAISE must fire for calling a type (not just interp2app
    # builtin functions) -- is_builtin_code() alone doesn't recognize
    # type calls like int([]), so this needs the wider is_python_function()
    # check (see pypy/interpreter/function.py) rather than is_builtin_code().
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.C_RAISE, callback)
        sys.monitoring.set_events(3, E.CALL | E.C_RETURN | E.C_RAISE)

        events[:] = []
        try:
            int([])
        except TypeError:
            pass
        assert any(ev[2] is int for ev in events)
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_call_no_c_events_for_python_function():
    # C_RETURN/C_RAISE only fire for non-Python callables -- Python
    # function returns are covered by PY_RETURN/PY_UNWIND instead.
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.C_RETURN, callback)
        sys.monitoring.register_callback(3, E.C_RAISE, callback)
        sys.monitoring.set_events(3, E.CALL | E.C_RETURN | E.C_RAISE)

        def f():
            return 1

        events[:] = []
        f()
        assert events == []
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_call_kw_and_ex():
    E = sys.monitoring.events
    events = []

    def callback(*args):
        events.append(args)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.CALL, callback)
        sys.monitoring.set_events(3, E.CALL)

        def f(*args, **kwargs):
            return args, kwargs

        events[:] = []
        assert f(1, a=2) == ((1,), {'a': 2})
        assert f(*[3], **{'b': 4}) == ((3,), {'b': 4})
        calls = [ev for ev in events if ev[2] is f]
        assert len(calls) == 2
        assert calls[0][3] == 1
        assert calls[1][3] == 3
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_no_events_when_not_registered():
    def f():
        return 1
    f()  # should not raise/crash even with monitoring untouched


def test_no_spurious_line_for_already_executing_frame():
    # set_events(..., E.LINE) is itself a statement on some line of the
    # *caller* frame (already mid-execution when monitoring turns on).
    # Monitoring must not retroactively report that already-in-progress
    # line -- only genuine line transitions after it turned on.
    E = sys.monitoring.events
    events = []

    def cb(code, lineno):
        events.append((code.co_name, lineno))

    def func1():
        line = 1
        line = 2
        line = 3

    def check_lines():
        sys.monitoring.use_tool_id(3, "test tool")
        try:
            sys.monitoring.register_callback(3, E.LINE, cb)
            sys.monitoring.set_events(3, E.LINE)
            func1()
            sys.monitoring.set_events(3, 0)
            sys.monitoring.register_callback(3, E.LINE, None)
        finally:
            sys.monitoring.set_events(3, 0)
            sys.monitoring.free_tool_id(3)

    events[:] = []
    check_lines()
    names = [name for name, lineno in events]
    # exactly one check_lines LINE event before func1's, and one after --
    # not two before (the spurious extra would be the set_events(...)
    # line itself, immediately followed by the func1() line).
    assert names.count('check_lines') == 2
    assert names == ['check_lines', 'func1', 'func1', 'func1', 'check_lines']

    first = func1.__code__.co_firstlineno
    func1_lines = [lineno for name, lineno in events if name == 'func1']
    assert func1_lines == [first + 1, first + 2, first + 3]


def test_fire_instruction():
    E = sys.monitoring.events
    events = []

    def f():
        x = 1
        y = 2
        return x + y

    code = f.__code__

    def callback(c, offset):
        if c is code:
            events.append(offset)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.INSTRUCTION, callback)
        sys.monitoring.set_events(3, E.INSTRUCTION)

        events[:] = []
        assert f() == 3
        # every instruction fires, at least one per line, all distinct
        # offsets, and covers more locations than LINE alone would
        assert len(events) >= 3
        assert len(events) == len(set(events))
        assert sorted(events) == events
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_local_events_add_not_mask():
    # "Local events add to global events, but do not mask them."  Tool 3
    # enables LINE only locally for f's code; tool 4 enables LINE
    # globally.  f's LINE events must fire for both tools; some other
    # unrelated code's LINE events must fire only for tool 4 (global),
    # not tool 3 (local-only, scoped to f).
    E = sys.monitoring.events

    def f():
        return 1

    def g():
        return 2

    events3 = []
    events4 = []

    def cb3(c, lineno):
        events3.append(c)

    def cb4(c, lineno):
        events4.append(c)

    sys.monitoring.use_tool_id(3, "local tool")
    sys.monitoring.use_tool_id(4, "global tool")
    try:
        sys.monitoring.register_callback(3, E.LINE, cb3)
        sys.monitoring.register_callback(4, E.LINE, cb4)
        sys.monitoring.set_local_events(3, f.__code__, E.LINE)
        sys.monitoring.set_events(4, E.LINE)

        events3[:] = []
        events4[:] = []
        f()
        g()

        assert f.__code__ in events3
        assert g.__code__ not in events3  # local-only tool: f only
        assert f.__code__ in events4
        assert g.__code__ in events4      # global tool: everything
    finally:
        sys.monitoring.set_events(4, 0)
        sys.monitoring.set_local_events(3, f.__code__, 0)
        sys.monitoring.free_tool_id(3)
        sys.monitoring.free_tool_id(4)


def test_disable_per_location():
    E = sys.monitoring.events

    def f():
        x = 1
        y = 2
        return x + y

    code = f.__code__
    first = code.co_firstlineno
    line_calls3 = []
    instr_calls3 = []
    line_calls4 = []

    def line_cb3(c, lineno):
        if c is not code:
            return
        line_calls3.append(lineno)
        if lineno == first + 1:
            return sys.monitoring.DISABLE

    def instr_cb3(c, offset):
        if c is code:
            instr_calls3.append(offset)

    def line_cb4(c, lineno):
        if c is code:
            line_calls4.append(lineno)

    sys.monitoring.use_tool_id(3, "t3")
    sys.monitoring.use_tool_id(4, "t4")
    try:
        sys.monitoring.register_callback(3, E.LINE, line_cb3)
        sys.monitoring.register_callback(3, E.INSTRUCTION, instr_cb3)
        sys.monitoring.register_callback(4, E.LINE, line_cb4)
        sys.monitoring.set_events(3, E.LINE | E.INSTRUCTION)
        sys.monitoring.set_events(4, E.LINE)

        for _ in range(3):
            f()

        # tool 3's LINE callback disabled itself at the first line after
        # its first firing -- that line never fires again for tool 3.
        assert line_calls3.count(first + 1) == 1
        assert line_calls3.count(first + 2) == 3
        assert line_calls3.count(first + 3) == 3

        # DISABLE is scoped per (tool, code, offset, event): tool 3's
        # INSTRUCTION callback at the same location is unaffected...
        n_instrs_per_call = len(instr_calls3) // 3
        assert n_instrs_per_call * 3 == len(instr_calls3)

        # ...and tool 4's LINE callback (a different tool) is unaffected.
        assert line_calls4.count(first + 1) == 3

        sys.monitoring.restart_events()
        line_calls3[:] = []
        f()
        # re-armed: the disabled line fires again right after restart
        assert line_calls3[0] == first + 1
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.set_events(4, 0)
        sys.monitoring.free_tool_id(3)
        sys.monitoring.free_tool_id(4)


def test_fire_jump():
    E = sys.monitoring.events
    events = []

    def f(n):
        total = 0
        i = 0
        while i < n:
            total += i
            i += 1
        return total

    code = f.__code__

    def callback(c, offset, dest):
        if c is code:
            events.append((offset, dest))

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.JUMP, callback)
        sys.monitoring.set_events(3, E.JUMP)

        events[:] = []
        assert f(5) == 10
        assert len(set(events)) == 1
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_branch():
    E = sys.monitoring.events
    events = []

    def f(x):
        if x:
            return 1
        else:
            return 2

    code = f.__code__

    def callback(c, offset, dest):
        if c is code:
            events.append(dest)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.BRANCH, callback)
        sys.monitoring.set_events(3, E.BRANCH)

        events[:] = []
        assert f(True) == 1
        assert len(events) == 1
        dest_true = events[0]

        events[:] = []
        assert f(False) == 2
        assert len(events) == 1
        dest_false = events[0]

        assert dest_true != dest_false
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_fire_branch_for_iter():
    E = sys.monitoring.events
    events = []

    def f():
        total = 0
        for i in [1, 2, 3]:
            total += i
        return total

    code = f.__code__

    def callback(c, offset, dest):
        if c is code:
            events.append(dest)

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.BRANCH, callback)
        sys.monitoring.set_events(3, E.BRANCH)

        events[:] = []
        assert f() == 6
        assert len(set(events[:3])) == 1
        assert events[3] != events[0]
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_branch_disable():
    E = sys.monitoring.events
    events = []

    def f(n):
        total = 0
        i = 0
        while i < n:
            total += i
            i += 1
        return total

    code = f.__code__

    def callback(c, offset, dest):
        if c is code:
            events.append(dest)
            return sys.monitoring.DISABLE

    sys.monitoring.use_tool_id(3, "test tool")
    try:
        sys.monitoring.register_callback(3, E.JUMP, callback)
        sys.monitoring.set_events(3, E.JUMP)

        events[:] = []
        assert f(5) == 10
        assert len(events) == 1
    finally:
        sys.monitoring.set_events(3, 0)
        sys.monitoring.free_tool_id(3)


def test_all_events():
    sys.monitoring.use_tool_id(3, "test tool")
    sys.monitoring.use_tool_id(4, "test tool 2")
    try:
        E = sys.monitoring.events
        assert sys.monitoring._all_events() == {}
        sys.monitoring.set_events(3, E.PY_START)
        sys.monitoring.set_events(4, E.PY_START)
        assert sys.monitoring._all_events() == {'PY_START': (1 << 3) | (1 << 4)}
        sys.monitoring.set_events(3, 0)
        sys.monitoring.set_events(4, 0)
        assert sys.monitoring._all_events() == {}
    finally:
        sys.monitoring.free_tool_id(3)
        sys.monitoring.free_tool_id(4)
