import py
import os.path
from pypy.module.sys.state import getinitialpath, find_executable
from pypy.module.sys.version import PYPY_VERSION, CPYTHON_VERSION

def build_hierarchy(prefix):
    dirname = '%d.%d' % CPYTHON_VERSION[:2]
    a = prefix.join('lib_pypy').ensure(dir=1)
    b = prefix.join('lib-python', dirname).ensure(dir=1)
    return a, b


def test_stdlib_in_prefix(tmpdir):
    dirs = build_hierarchy(tmpdir)
    path = getinitialpath(None, str(tmpdir))
    # we get at least 'dirs', and maybe more (e.g. plat-linux2)
    assert path[:len(dirs)] == map(str, dirs)

def test_include_libtk(tmpdir):
    lib_pypy, lib_python = build_hierarchy(tmpdir)
    lib_tk = lib_python.join('lib-tk')
    path = getinitialpath(None, str(tmpdir))
    assert lib_tk in path


def test_find_executable(tmpdir, monkeypatch):
    from pypy.module.sys import state
    # /tmp/a/pypy
    # /tmp/b/pypy
    # /tmp/c
    a = tmpdir.join('a').ensure(dir=True)
    b = tmpdir.join('b').ensure(dir=True)
    c = tmpdir.join('c').ensure(dir=True)
    a.join('pypy').ensure(file=True)
    b.join('pypy').ensure(file=True)
    #
    # if there is already a slash, don't do anything
    monkeypatch.chdir(tmpdir)
    assert find_executable('a/pypy') == a.join('pypy')
    #
    # if path is None, try abspath (if the file exists)
    monkeypatch.setenv('PATH', None)
    monkeypatch.chdir(a)
    assert find_executable('pypy') == a.join('pypy')
    monkeypatch.chdir(tmpdir) # no pypy there
    assert find_executable('pypy') == ''
    #
    # find it in path
    monkeypatch.setenv('PATH', str(a))
    assert find_executable('pypy') == a.join('pypy')
    #
    # find it in the first dir in path
    monkeypatch.setenv('PATH', '%s%s%s' % (b, os.pathsep, a))
    assert find_executable('pypy') == b.join('pypy')
    #
    # find it in the second, because in the first it's not there
    monkeypatch.setenv('PATH', '%s%s%s' % (c, os.pathsep, a))
    assert find_executable('pypy') == a.join('pypy')
    # if pypy is found but it's not a file, ignore it
    c.join('pypy').ensure(dir=True)
    assert find_executable('pypy') == a.join('pypy')
    #
    monkeypatch.setattr(state, 'we_are_translated', lambda: True)
    monkeypatch.setattr(state, 'IS_WINDOWS', True)
    monkeypatch.setenv('PATH', str(a))
    a.join('pypy.exe').ensure(file=True)
    assert find_executable('pypy') == a.join('pypy.exe')
