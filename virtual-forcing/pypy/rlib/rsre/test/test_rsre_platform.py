
from pypy.rlib.rsre._rsre_platform import *

def test_tolower():
    assert tolower(ord('A')) == ord('a')
