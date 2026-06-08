"""Tests for error message formatting in extended call syntax (*args, **kwargs)."""
import pytest


def test_function_name_includes_module():
    # When __module__ is a non-builtins value, errors use "module.qualname()" format
    def f(**kwargs):
        pass
    f.__module__ = 'some.module'
    with pytest.raises(TypeError) as exc_info:
        f(**{'a': 1}, **{'a': 2})
    assert str(exc_info.value).startswith('some.module.')


def test_function_name_no_prefix_for_builtins_module():
    # When __module__ is 'builtins', no module prefix is added
    def f(**kwargs):
        pass
    f.__module__ = 'builtins'
    with pytest.raises(TypeError) as exc_info:
        f(**{'a': 1}, **{'a': 2})
    msg = str(exc_info.value)
    assert 'f() got multiple values' in msg
    assert not msg.startswith('builtins.')


def test_function_name_no_prefix_when_module_is_none():
    # When __module__ is None, no module prefix
    def f(**kwargs):
        pass
    f.__module__ = None
    with pytest.raises(TypeError) as exc_info:
        f(**{'a': 1}, **{'a': 2})
    assert 'f() got multiple values' in str(exc_info.value)


def test_non_function_callable_uses_repr():
    # For non-function callables like None, the error uses repr(obj) as prefix
    nothing = None
    h = lambda: None
    with pytest.raises(TypeError) as exc_info:
        nothing(*h)
    assert str(exc_info.value).startswith('None argument after *')
    with pytest.raises(TypeError) as exc_info:
        nothing(**h)
    assert str(exc_info.value).startswith('None argument after **')


def test_id_takes_no_keyword_arguments():
    with pytest.raises(TypeError) as exc_info:
        id(1, **{'foo': 1})
    assert 'takes no keyword arguments' in str(exc_info.value)
