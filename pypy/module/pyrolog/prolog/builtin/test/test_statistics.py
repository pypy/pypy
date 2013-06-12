import py
import time
from prolog.interpreter.continuation import Engine
from prolog.interpreter.test.tool import collect_all, assert_false, assert_true
from prolog.builtin.statistics import Clocks

e = Engine()
def test_statistics():
    assert_true("statistics(runtime, X).", e)
    
def test_statistics_builds_list():
    assert_true('statistics(runtime, [A,B]), number(A), number(B).', e)
    
def test_statistics_runtime_total():
    # first call returns total runtime in both list items
    e.clocks.startup()
    vars = assert_true("statistics(runtime, [A,B]).", e)
    assert vars['A'].num <= vars['B'].num
    
def test_statistics_runtime_since_last_call():
    e.clocks.startup()
    # succesive call return total runtime and time since last call
    vars1 = assert_true("statistics(runtime, _), statistics(runtime, [A,B]).", e)
    vars2 = assert_true("statistics(runtime, _), statistics(runtime, [A,B]).", e)
    assert vars2['A'].num != vars2['B'].num
    assert vars1['A'].num <= vars2['A'].num
    
def test_statistics_walltime_total():
    e.clocks.startup()
    # first call returns total runtime in both list items
    vars = assert_true("statistics(walltime, [A,B]).", e)
    assert vars['A'].num == vars['B'].num
    assert vars['A'].num != 0

def test_statistics_walltime_since_last_call():
    # succesive call return total runtime and time since last call
    e.clocks.startup()
    # first call returns total runtime in both list items
    vars1 = assert_true("statistics(walltime, _), statistics(walltime, [A,B]).", e)
    vars2 = assert_true("statistics(walltime, _), statistics(walltime, [A,B]).", e)
    assert vars2['A'].num != vars2['B'].num
    assert vars1['A'].num <= vars2['A'].num

def test_statistics_walltime_progresses():
    # succesive call return total runtime and time since last call
    e.clocks.startup()
    v1 = assert_true("statistics(walltime, _), statistics(walltime, [A,B]).", e)
    time.sleep(2)
    v2 = assert_true("statistics(walltime, _), statistics(walltime, [C,D]).", e)
    assert v1['A'] != v1['B']
    assert 1000 <= v2['C'].num - v1['A'].num <= 3000
