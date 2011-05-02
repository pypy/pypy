
import py
from pypy.tool.autopath import pypydir
from pypy.tool.release import package
from pypy.module.sys.version import  CPYTHON_VERSION
import tarfile, zipfile, os, sys

def test_dir_structure(test='test'):
    # make sure we have sort of pypy-c
    if sys.platform == 'win32':
        basename = 'pypy-c.exe'
        rename_pypy_c = 'pypy-c'
    else:
        basename = 'pypy-c'
        rename_pypy_c = 'pypy'
    pypy_c = py.path.local(pypydir).join('translator', 'goal', basename)
    if not pypy_c.check():
        os.system("echo faked_pypy_c> %s" % (pypy_c,))
        fake_pypy_c = True
    else:
        fake_pypy_c = False
    try:
        builddir = package.package(py.path.local(pypydir).dirpath(), test,
                                   rename_pypy_c)
        prefix = builddir.join(test)
        cpyver = '%d.%d' % CPYTHON_VERSION[:2]
        assert prefix.join('lib-python', cpyver, 'test').check()
        if sys.platform == 'win32':
            assert prefix.join('pypy-c.exe').check()
        else:
            assert prefix.join('bin', 'pypy').check()
        assert prefix.join('lib_pypy', 'syslog.py').check()
        assert not prefix.join('lib_pypy', 'py').check()
        assert not prefix.join('lib_pypy', 'ctypes_configure').check()
        assert prefix.join('LICENSE').check()
        assert prefix.join('README').check()
        if package.USE_ZIPFILE_MODULE:
            zh = zipfile.ZipFile(str(builddir.join('%s.zip' % test)))
            assert zh.open('%s/lib_pypy/syslog.py' % test)
        else:
            th = tarfile.open(str(builddir.join('%s.tar.bz2' % test)))
            assert th.getmember('%s/lib_pypy/syslog.py' % test)

        # the headers file could be not there, because they are copied into
        # trunk/include only during translation
        includedir = py.path.local(pypydir).dirpath().join('include')
        def check_include(name):
            if includedir.join(name).check(file=True):
                member = '%s/include/%s' % (test, name)
                if package.USE_ZIPFILE_MODULE:
                    assert zh.open(member)
                else:
                    assert th.getmember(member)
        check_include('Python.h')
        check_include('modsupport.h')
        check_include('pypy_decl.h')
    finally:
        if fake_pypy_c:
            pypy_c.remove()

def test_with_zipfile_module():
    from pypy.tool.release import package
    prev = package.USE_ZIPFILE_MODULE
    try:
        package.USE_ZIPFILE_MODULE = True
        test_dir_structure(test='testzipfile')
    finally:
        package.USE_ZIPFILE_MODULE = prev
