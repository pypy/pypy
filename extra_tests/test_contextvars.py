from contextvars import ContextVar

def test_contextvar_generic_alias():
    assert ContextVar[int].__origin__ is ContextVar
