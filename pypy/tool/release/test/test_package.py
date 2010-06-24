
import py
from pypy.tool.autopath import pypydir
from pypy.tool.release.package import package
from pypy.module.sys.version import  CPYTHON_VERSION
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
        prefix = builddir.join('test')
        cpyver = '%d.%d.%d' % CPYTHON_VERSION[:3]
        assert prefix.join('lib-python', cpyver, 'test').check()
        assert prefix.join('bin', 'pypy-c').check()
        assert prefix.join('lib_pypy', 'syslog.py').check()
        assert not prefix.join('lib_pypy', 'py').check()
        assert not prefix.join('lib_pypy', 'ctypes_configure').check()
        assert prefix.join('LICENSE').check()
        assert prefix.join('README').check()
        th = tarfile.open(str(builddir.join('test.tar.bz2')))
        assert th.getmember('test/lib_pypy/syslog.py')
    finally:
        if fake_pypy_c:
            pypy_c.remove()
