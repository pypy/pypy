import pytest
try:
    import nt as posix
except ImportError:
    import posix


def test_cpu_count():
    cc = posix.cpu_count()
    assert cc is None or (isinstance(cc, int) and cc > 0)

def test_putenv_invalid_name():
    with pytest.raises(ValueError):
        posix.putenv("foo=bar", "xxx")
