import _pickle_support
import pytest

def test_valid():
    with pytest.raises(ValueError):
        _pickle_support.builtin_code("")

