
import py
from pypy.tool.version import get_mercurial_info

def test_get_mercurial_info():
    assert get_mercurial_info(py.path.local.sysfind(
        'completely broken mercurial'))
