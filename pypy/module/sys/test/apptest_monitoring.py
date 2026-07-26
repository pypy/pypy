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


def test_set_events_c_return_independent():
    E = sys.monitoring.events
    raises(ValueError, sys.monitoring.set_events, 3, E.C_RETURN)
    raises(ValueError, sys.monitoring.set_events, 3, E.C_RAISE)
    # allowed together with CALL, and C_RETURN/C_RAISE bits are dropped
    sys.monitoring.set_events(3, E.CALL | E.C_RETURN | E.C_RAISE)
    assert sys.monitoring.get_events(3) == E.CALL
    sys.monitoring.set_events(3, 0)


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
