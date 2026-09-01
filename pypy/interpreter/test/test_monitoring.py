import py

from pypy.interpreter.pymonitoring import (
    CodeMonitoringState, INSTRUCTION, LINE, MonitoringState)
from rpython.rtyper.test.test_llinterp import interpret


def test_disabled_tool_masks():
    state = CodeMonitoringState()
    assert state.disabled is None

    state.disable(1, 4, LINE, 8)
    assert len(state.disabled) == 10
    assert len(state.disabled[LINE]) == 8
    assert ord(state.disabled[LINE][2]) == 1 << 1
    assert state.is_disabled(1, 4, LINE)
    assert not state.is_disabled(2, 4, LINE)
    assert not state.is_disabled(1, 6, LINE)

    state.disable(4, 4, LINE, 8)
    assert ord(state.disabled[LINE][2]) == (1 << 1) | (1 << 4)
    assert state.is_disabled(1, 4, LINE)
    assert state.is_disabled(4, 4, LINE)


def test_disabled_events_have_separate_arrays():
    state = CodeMonitoringState()
    state.disable(2, 6, LINE, 8)
    state.disable(3, 6, INSTRUCTION, 8)

    assert state.is_disabled(2, 6, LINE)
    assert not state.is_disabled(3, 6, LINE)
    assert state.is_disabled(3, 6, INSTRUCTION)
    assert not state.is_disabled(2, 6, INSTRUCTION)
    assert state.disabled[LINE] is not state.disabled[INSTRUCTION]


def test_disabled_query_version():
    state = CodeMonitoringState()
    version = state.version
    state.disable(1, 0, LINE, 1)
    assert state.version is not version
    py.test.raises(AssertionError, state._is_disabled,
                   version, 1, 0, LINE)


def test_pycode_monitoring_state_is_lazy_and_restartable(space):
    code = space.createcompiler().compile(
        'x = 1', 'monitoring-test', 'exec', 0)
    assert code.monitoring_state is None

    code.monitoring_set_local_events(1, 0)
    assert code.monitoring_state is None

    code.monitoring_disable(1, 0, LINE)
    state = code.monitoring_state
    assert state is not None
    assert len(state.disabled[LINE]) == len(code.co_code) >> 1
    assert state.is_disabled(1, 0, LINE)

    version = state.version
    code.monitoring_restart_events()
    assert state.disabled is None
    assert state.version is not version
    assert not state.is_disabled(1, 0, LINE)


def test_disabled_tool_masks_rtype():
    def check():
        state = CodeMonitoringState()
        state.disable(1, 4, LINE, 8)
        state.disable(4, 4, LINE, 8)
        state.disable(3, 6, INSTRUCTION, 8)
        if not state.is_disabled(1, 4, LINE):
            return 1
        if not state.is_disabled(4, 4, LINE):
            return 2
        if state.is_disabled(3, 4, LINE):
            return 3
        if not state.is_disabled(3, 6, INSTRUCTION):
            return 4
        return 0

    assert interpret(check, []) == 0


def test_callback_version():
    state = MonitoringState(None)
    callback1 = object()
    callback2 = object()

    initial_version = state.callbacks_version
    assert state.get_callback(2, LINE) is None
    assert state.set_callback(2, LINE, callback1) is None
    assert state.callbacks_version is not initial_version
    assert state.get_callback(2, LINE) is callback1
    py.test.raises(AssertionError, state._get_callback,
                   initial_version, 2 * 17 + LINE)

    version = state.callbacks_version
    assert state.set_callback(2, LINE, callback1) is callback1
    assert state.callbacks_version is version

    assert state.set_callback(2, LINE, callback2) is callback1
    assert state.callbacks_version is not version
    assert state.get_callback(2, LINE) is callback2

    assert state.set_callback(2, LINE, None) is callback2
    assert state.get_callback(2, LINE) is None


def test_callback_version_rtype():
    class Callback(object):
        pass

    def check():
        state = MonitoringState(None)
        callback1 = Callback()
        callback2 = Callback()
        if state.set_callback(2, LINE, callback1) is not None:
            return 1
        if state.get_callback(2, LINE) is not callback1:
            return 2
        if state.set_callback(2, LINE, callback2) is not callback1:
            return 3
        if state.get_callback(2, LINE) is not callback2:
            return 4
        if state.set_callback(2, LINE, None) is not callback2:
            return 5
        if state.get_callback(2, LINE) is not None:
            return 6
        return 0

    assert interpret(check, []) == 0
