import pytest

def test_delete_attrs():
    # for whatever reason CPython raises TypeError instead of AttributeError
    # here
    for attr in ["__cause__", "__context__", "args", "__traceback__", "__suppress_context__"]:
        with pytest.raises(TypeError) as info:
            delattr(Exception(), attr)
        assert str(info.value).endswith("may not be deleted")
