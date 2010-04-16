
from pypy.rlib.rlocale import setlocale, LC_CTYPE

def test_setlocale():
    oldlocale = setlocale(LC_CTYPE, None)
    try:
        pass
    finally:
        setlocale(LC_CTYPE, oldlocale)
