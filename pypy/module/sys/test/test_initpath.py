import py
import os.path
from pypy.module.sys.initpath import (compute_stdlib_path, find_executable,
                                      find_stdlib, resolvedirof,
                                      pypy_init_home, pypy_init_free)
from pypy.module.sys.version import PYPY_VERSION, CPYTHON_VERSION
from rpython.rtyper.lltypesystem import rffi

def build_hierarchy(prefix):
    dirname = '%d.%d' % CPYTHON_VERSION[:2]
    a = prefix.join('lib_pypy').ensure(dir=1)
    b = prefix.join('lib-python', dirname).ensure(dir=1)
    return a, b

def test_find_stdlib(tmpdir):
    bin_dir = tmpdir.join('bin').ensure(dir=True)
    pypy = bin_dir.join('pypy').ensure(file=True)
    build_hierarchy(tmpdir)
    path, prefix = find_stdlib(None, str(pypy))
    assert prefix == tmpdir
    # in executable is None look for stdlib based on the working directory
    # see lib-python/2.7/test/test_sys.py:test_executable
    _, prefix = find_stdlib(None, '')
    cwd = os.path.dirname(os.path.realpath(__file__))
    assert prefix is not None
    assert cwd.startswith(str(prefix))

@py.test.mark.skipif('not hasattr(os, "symlink")')
def test_find_stdlib_follow_symlink(tmpdir):
    pypydir = tmpdir.join('opt', 'pypy-xxx')
    pypy = pypydir.join('bin', 'pypy').ensure(file=True)
    build_hierarchy(pypydir)
    pypy_sym = tmpdir.join('pypy_sym')
    os.symlink(str(pypy), str(pypy_sym))
    path, prefix = find_stdlib(None, str(pypy_sym))
    assert prefix == pypydir

def test_pypy_init_home():
    p = pypy_init_home()
    assert p
    s = rffi.charp2str(p)
    pypy_init_free(p)
    print s
    assert os.path.exists(s)

def test_compute_stdlib_path(tmpdir):
    dirs = build_hierarchy(tmpdir)
    path = compute_stdlib_path(None, str(tmpdir))
    # we get at least 'dirs', and maybe more (e.g. plat-linux2)
    assert path[:len(dirs)] == map(str, dirs)

def test_include_libtk(tmpdir):
    lib_pypy, lib_python = build_hierarchy(tmpdir)
    lib_tk = lib_python.join('lib-tk')
    path = compute_stdlib_path(None, str(tmpdir))
    assert lib_tk in path

def test_find_executable(tmpdir, monkeypatch):
    from pypy.module.sys import initpath
    tmpdir = py.path.local(os.path.realpath(str(tmpdir)))
    # /tmp/a/pypy
    # /tmp/b/pypy
    # /tmp/c
    a = tmpdir.join('a').ensure(dir=True)
    b = tmpdir.join('b').ensure(dir=True)
    c = tmpdir.join('c').ensure(dir=True)
    a.join('pypy').ensure(file=True)
    b.join('pypy').ensure(file=True)
    #
    monkeypatch.setattr(os, 'access', lambda x, y: True)
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
    # if pypy is found but it's not executable, ignore it
    monkeypatch.setattr(os, 'access', lambda x, y: False)
    assert find_executable('pypy') == ''
    #
    monkeypatch.setattr(os, 'access', lambda x, y: True)
    monkeypatch.setattr(initpath, 'we_are_translated', lambda: True)
    monkeypatch.setattr(initpath, '_WIN32', True)
    monkeypatch.setenv('PATH', str(a))
    a.join('pypy.exe').ensure(file=True)
    assert find_executable('pypy') == a.join('pypy.exe')

def test_resolvedirof(tmpdir):
    assert resolvedirof('') == os.path.abspath(os.path.join(os.getcwd(), '..'))
    foo = tmpdir.join('foo').ensure(dir=True)
    bar = tmpdir.join('bar').ensure(dir=True)
    myfile = foo.join('myfile').ensure(file=True)
    assert resolvedirof(str(myfile)) == foo
    if hasattr(myfile, 'mksymlinkto'):
        myfile2 = bar.join('myfile')
        myfile2.mksymlinkto(myfile)
        assert resolvedirof(str(myfile2)) == foo
