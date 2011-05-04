import autopath
import os, sys, stat, errno
from pypy.translator.sandbox.pypy_interact import PyPySandboxedProc
from pypy.translator.interactive import Translation
from pypy.module.sys.version import CPYTHON_VERSION

VERSION = '%d.%d' % CPYTHON_VERSION[:2]
SITE_PY_CONTENT = open(os.path.join(autopath.pypydir,
                                    '..',
                                    'lib-python',
                                    'modified-' + VERSION, 'site.py'),
                       'rb').read()
ERROR_TEXT = os.strerror(errno.ENOENT)

def assert_(cond, text):
    if not cond:
        print "assert failed:", text
        raise AssertionError

def mini_pypy_like_entry_point(argv):
    """An RPython standalone executable that does the same kind of I/O as
    PyPy when it starts up.
    """
    assert_(len(argv) == 3, "expected len(argv) == 3")
    assert_(argv[1] == 'foo', "bad argv[1]")
    assert_(argv[2] == 'bar', "bad argv[2]")
    env = os.environ.items()
    assert_(len(env) == 0, "empty environment expected")
    assert_(argv[0] == '/bin/pypy-c', "bad argv[0]")
    st = os.lstat('/bin/pypy-c')
    assert_(stat.S_ISREG(st.st_mode), "bad st_mode for /bin/pypy-c")
    for dirname in ['/bin/lib-python/' + VERSION, '/bin/lib_pypy']:
        st = os.stat(dirname)
        assert_(stat.S_ISDIR(st.st_mode), "bad st_mode for " + dirname)
    assert_(os.environ.get('PYTHONPATH') is None, "unexpected $PYTHONPATH")
    try:
        os.stat('site')
    except OSError:
        pass
    else:
        assert_(False, "os.stat('site') should have failed")
    st = os.stat('/bin/lib-python/modified-%s/site.py' % VERSION)
    assert_(stat.S_ISREG(st.st_mode), "bad st_mode for .../site.py")
    try:
        os.stat('/bin/lib-python/modified-%s/site.pyc' % VERSION)
    except OSError:
        pass
    else:
        assert_(False, "os.stat('....pyc') should have failed")
    fd = os.open('/bin/lib-python/modified-%s/site.py' % VERSION,
                 os.O_RDONLY, 0666)
    length = 8192
    ofs = 0
    while True:
        data = os.read(fd, length)
        if not data: break
        end = ofs+length
        if end > len(SITE_PY_CONTENT):
            end = len(SITE_PY_CONTENT)
        assert_(data == SITE_PY_CONTENT[ofs:end], "bad data from site.py")
        ofs = end
    os.close(fd)
    assert_(ofs == len(SITE_PY_CONTENT), "not enough data from site.py")
    assert_(os.getcwd() == '/tmp', "bad cwd")
    assert_(os.strerror(errno.ENOENT) == ERROR_TEXT, "bad strerror(ENOENT)")
    assert_(os.isatty(0), "isatty(0) returned False")
    # an obvious 'attack'
    try:
        os.open('/spam', os.O_RDWR | os.O_CREAT, 0666)
    except OSError:
        pass
    else:
        assert_(False, "os.open('/spam') should have failed")
    return 0


def setup_module(mod):
    t = Translation(mini_pypy_like_entry_point, backend='c',
                   standalone=True, sandbox=True)
    mod.executable = str(t.compile())


def test_run():
    sandproc = PyPySandboxedProc(executable, ['foo', 'bar'])
    returncode = sandproc.interact()
    assert returncode == 0
