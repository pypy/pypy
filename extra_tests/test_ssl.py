import pytest
import _ssl
import os


@pytest.mark.skipif(os.name != 'posix', reason="needs /dev/null")
def test_invalid_file():
    # gh-5120: do not segfault
    with pytest.raises(_ssl.SSLError):
        cert = _ssl._test_decode_cert("/dev/null")
