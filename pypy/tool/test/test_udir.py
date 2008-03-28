
from pypy.tool import udir

def test_udir():
    res = udir.svn_info('http://codespeak.net/svn/pypy/dist/pypy/tool')
    assert res == 'dist'
    res = udir.svn_info('http://codespeak.net/svn/pypy/branch/stuff/pypy/tool')
    assert res == 'stuff'
