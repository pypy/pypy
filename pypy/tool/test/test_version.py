
from pypy.tool.version import get_mercurial_info

def test_get_mercurial_info():
    assert get_mercurial_info('completely broken mercurial')
