
import py
from pypy.conftest import pypydir
from pypy.tool.release import package
from pypy.module.sys.version import  CPYTHON_VERSION
import tarfile, zipfile, sys

def test_dir_structure(test='test'):
    # make sure we have sort of pypy-c
    if sys.platform == 'win32':
        basename = 'pypy-c.exe'
        rename_pypy_c = 'pypy-c'
        exe_name_in_archive = 'pypy-c.exe'
    else:
        basename = 'pypy-c'
        rename_pypy_c = 'pypy'
        exe_name_in_archive = 'bin/pypy'
    pypy_c = py.path.local(pypydir).join('goal', basename)
    if not pypy_c.check():
        if sys.platform == 'win32':
            assert False, "test on win32 requires exe"
        pypy_c.write("#!/bin/sh")
        pypy_c.chmod(0755)
        fake_pypy_c = True
    else:
        fake_pypy_c = False
    try:
        builddir = package.package(py.path.local(pypydir).dirpath(), test,
                                   rename_pypy_c)
        prefix = builddir.join(test)
        cpyver = '%d.%d' % CPYTHON_VERSION[:2]
        assert prefix.join('lib-python', cpyver, 'test').check()
        assert prefix.join(exe_name_in_archive).check()
        assert prefix.join('lib_pypy', 'syslog.py').check()
        assert not prefix.join('lib_pypy', 'py').check()
        assert not prefix.join('lib_pypy', 'ctypes_configure').check()
        assert prefix.join('LICENSE').check()
        assert prefix.join('README.rst').check()
        if package.USE_ZIPFILE_MODULE:
            zh = zipfile.ZipFile(str(builddir.join('%s.zip' % test)))
            assert zh.open('%s/lib_pypy/syslog.py' % test)
        else:
            th = tarfile.open(str(builddir.join('%s.tar.bz2' % test)))
            syslog = th.getmember('%s/lib_pypy/syslog.py' % test)
            exe = th.getmember('%s/%s' % (test, exe_name_in_archive))
            assert syslog.mode == 0644
            assert exe.mode == 0755
            assert exe.uname == ''
            assert exe.gname == ''
            # The tar program on MacOSX or the FreeBSDs does not support
            # setting the numeric uid and gid when creating a tar file.
            if not(sys.platform == 'darwin' or sys.platform.startswith('freebsd')):
                assert exe.uid == 0
                assert exe.gid == 0

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
            else:
                print 'include file "%s" not found, are we translated?' % includedir.join(name)
        check_include('Python.h')
        check_include('modsupport.h')
        check_include('pypy_decl.h')
        check_include('numpy/arrayobject.h')
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

def test_fix_permissions(tmpdir):
    if sys.platform == 'win32':
        py.test.skip('needs to be more general for windows')
    def check(f, mode):
        assert f.stat().mode & 0777 == mode
    #
    mydir = tmpdir.join('mydir').ensure(dir=True)
    bin   = tmpdir.join('bin')  .ensure(dir=True)
    file1 = tmpdir.join('file1').ensure(file=True)
    file2 = mydir .join('file2').ensure(file=True)
    pypy  = bin   .join('pypy') .ensure(file=True)
    #
    mydir.chmod(0700)
    bin.chmod(0700)
    file1.chmod(0600)
    file2.chmod(0640)
    pypy.chmod(0700)
    #
    package.fix_permissions(tmpdir)
    check(mydir, 0755)
    check(bin,   0755)
    check(file1, 0644)
    check(file2, 0644)
    check(pypy,  0755)
