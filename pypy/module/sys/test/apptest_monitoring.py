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
