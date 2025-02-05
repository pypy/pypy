import pytest
import sys

@pytest.mark.skipif(sys.platform == 'win32', reason="works on win32")
def test_cant_import_msvcrt():
    with pytest.raises(ModuleNotFoundError) as info:
        import msvcrt
    assert info.value.name == "msvcrt"
