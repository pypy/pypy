import pytest

def test_delete_attrs():
    # for whatever reason CPython raises TypeError instead of AttributeError
    # here
    for attr in ["__cause__", "__context__", "args", "__traceback__", "__suppress_context__"]:
        with pytest.raises(TypeError) as info:
            delattr(Exception(), attr)
        assert str(info.value).endswith("may not be deleted")

def test_notes():
    base = BaseException()
    base.add_note('test note')
    assert base.__notes__ == ['test note']
    base.add_note('second note')
    assert base.__notes__ == ['test note', 'second note']
    with pytest.raises(TypeError):
        base.add_note(42)
    assert base.__notes__ == ['test note', 'second note']


def test_exception_group():
    # the actual tests are in extra_tests, this is a simple smoke test that the
    # integration into builtins works
    assert issubclass(ExceptionGroup, BaseExceptionGroup)
