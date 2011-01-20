import os, sys
import py
from pypy.tool.version import get_mercurial_info

def test_get_mercurial_info():
    assert get_mercurial_info(None)
    assert get_mercurial_info(os.devnull) == ('PyPy', '?', '?')
    assert get_mercurial_info(sys.executable) == ('PyPy', '?', '?')
