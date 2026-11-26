import pytest
from rpython.rtyper.lltypesystem.ll2ctypes import libc_name

YEAR_10000_CRASHES = False
if libc_name == 'msvcr90.dll':
    YEAR_10000_CRASHES = True

class AppTestTime:
    spaceconfig = {
        "usemodules": ['time', 'struct', 'binascii'],
    }

    @pytest.mark.skipif(YEAR_10000_CRASHES, reason='MSVC<10 crashes unconditionally')
    def test_large_year_does_not_crash(self):
        # may fail on windows but should not crash
        import time
        try:
            time.strftime('%Y', (10000, 0, 0, 0, 0, 0, 0, 0, 0))
        except ValueError:
            pass
