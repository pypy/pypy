
import py
from pypy.tool.autopath import pypydir
from pypy.tool.release.package import package
from pypy.module.sys.version import  CPYTHON_VERSION
import tarfile, os

def test_dir_structure(test='test'):
    # make sure we have sort of pypy-c
    pypy_c = py.path.local(pypydir).join('translator', 'goal', 'pypy-c')
    if not pypy_c.check():
        os.system("echo faked_pypy_c> %s" % (pypy_c,))
        fake_pypy_c = True
    else:
        fake_pypy_c = False
    try:
        builddir = package(py.path.local(pypydir).dirpath(), test)
        prefix = builddir.join(test)
        cpyver = '%d.%d.%d' % CPYTHON_VERSION[:3]
        assert prefix.join('lib-python', cpyver, 'test').check()
        assert prefix.join('bin', 'pypy').check()
        assert prefix.join('lib_pypy', 'syslog.py').check()
        assert not prefix.join('lib_pypy', 'py').check()
        assert not prefix.join('lib_pypy', 'ctypes_configure').check()
        assert prefix.join('LICENSE').check()
        assert prefix.join('README').check()
        th = tarfile.open(str(builddir.join('%s.tar.bz2' % test)))
        assert th.getmember('%s/lib_pypy/syslog.py' % test)

        # the headers file could be not there, because they are copied into
        # trunk/include only during translation
        includedir = py.path.local(pypydir).dirpath().join('include')
        def check_include(name):
            if includedir.join(name).check(file=True):
                assert th.getmember('%s/include/%s' % (test, name))
        check_include('Python.h')
        check_include('modsupport.inl')
        check_include('pypy_decl.h')
    finally:
        if fake_pypy_c:
            pypy_c.remove()

def test_with_tarfile_module():
    from pypy.tool.release import package
    prev = package.USE_TARFILE_MODULE
    try:
        package.USE_TARFILE_MODULE = True
        test_dir_structure(test='testtarfile')
    finally:
        package.USE_TARFILE_MODULE = prev
