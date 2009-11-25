
from pypy.tool import udir

def test_svn_info():
    res = udir.svn_info('http://codespeak.net/svn/pypy/dist/pypy/tool')
    assert res == 'dist'
    res = udir.svn_info('http://codespeak.net/svn/pypy/branch/stuff/pypy/tool')
    assert res == 'stuff'

def test_make_udir():
    root = str(udir.udir.ensure('make_udir', dir=1))
    p1 = udir.make_udir(dir=root)
    p2 = udir.make_udir(dir=root)
    assert p1.relto(root).startswith('usession-')
    assert p2.relto(root).startswith('usession-')
    assert p1.basename.endswith('-0')
    assert p2.basename.endswith('-1')

def test_make_udir_with_basename():
    root = str(udir.udir.ensure('make_udir', dir=1))
    p1 = udir.make_udir(dir=root, basename='foobar')
    assert p1.relto(root) == 'usession-foobar-0'
    p1 = udir.make_udir(dir=root, basename='-foobar')
    assert p1.relto(root) == 'usession-foobar-1'
    p1 = udir.make_udir(dir=root, basename='foobar-')
    assert p1.relto(root) == 'usession-foobar-2'
    p1 = udir.make_udir(dir=root, basename='-foobar-')
    assert p1.relto(root) == 'usession-foobar-3'
    p1 = udir.make_udir(dir=root, basename='')
    assert p1.relto(root) == 'usession-0'
    p1 = udir.make_udir(dir=root, basename='-')
    assert p1.relto(root) == 'usession-1'
