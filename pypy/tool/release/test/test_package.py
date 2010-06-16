
import py
from pypy.tool.autopath import pypydir
from pypy.tool.release.package import package
import tarfile, os

def test_dir_structure():
    # make sure we have sort of pypy-c
    pypy_c = py.path.local(pypydir).join('translator', 'goal', 'pypy-c')
    if not pypy_c.check():
        os.system("echo faked_pypy_c> %s" % (pypy_c,))
        fake_pypy_c = True
    else:
        fake_pypy_c = False
    try:
        builddir = package(py.path.local(pypydir).dirpath(), 'test')
        assert builddir.join('test', 'lib-python', '2.5.2', 'test').check()
        assert builddir.join('test', 'bin', 'pypy-c').check()
        assert builddir.join('test', 'pypy', 'lib', 'syslog.py').check()
        assert not builddir.join('test', 'pypy', 'lib', 'py').check()
        assert not builddir.join('test', 'pypy', 'lib', 'ctypes_configure').check()
        assert builddir.join('test', 'LICENSE').check()
        assert builddir.join('test', 'README').check()
        th = tarfile.open(str(builddir.join('test.tar.bz2')))
        assert th.getmember('test/pypy/lib/syslog.py')
    finally:
        if fake_pypy_c:
            pypy_c.remove()
