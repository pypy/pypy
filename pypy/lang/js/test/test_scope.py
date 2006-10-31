
""" test scope
"""

from pypy.lang.js.scope import ScopeManager


def test_scope_manager_search():
    sm = ScopeManager()
    sm.enter_scope()
    sm.add_variable("5", 5)
    assert sm.get_variable("5") == 5
    sm.enter_scope()
    assert sm.get_variable("5") == 5
    sm.add_variable("5", 6)
    assert sm.get_variable("5") == 6
    sm.leave_scope()
    assert sm.get_variable("5") == 5

def test_scope_manager_overlay():
    sm = ScopeManager()
    sm.enter_scope()
    sm.add_variable("5", 5)
    assert sm.get_variable("5") == 5
    sm.enter_scope()
    sm.add_variable("5", 6)
    assert sm.get_variable("5") == 6

def test_scope_manager_updown():
    sm = ScopeManager()
    sm.enter_scope()
    sm.add_variable("5", 5)
    sm.enter_scope()
    sm.add_variable("5", 6)
    sm.leave_scope()
    assert sm.get_variable("5") == 5
