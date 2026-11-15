import os
import py
from pypy import pypydir
from pypy.tool.release import package
from pypy.module.sys.version import  CPYTHON_VERSION
from rpython.tool.udir import udir
import tarfile, zipfile, sys

class TestPackaging:
    def setup_class(cls):
        # make sure we have sort of pypy-c
        if sys.platform == 'win32':
            basename = 'pypy-c.exe'
            cls.rename_pypy_c = 'pypy-c'
            cls.exe_name_in_archive = 'pypy-c.exe'
        else:
            basename = 'pypy-c'
            cls.rename_pypy_c = package.POSIX_EXE
            cls.exe_name_in_archive = os.path.join('bin', package.POSIX_EXE)
        cls.pypy_c = py.path.local(pypydir).join('goal', basename)

    def test_dir_structure(self, test='test'):
        retval, builddir = package.package(
            '--without-cffi',
            '--archive-name', test,
            '--rename_pypy_c', self.rename_pypy_c,
            _fake=True)
        assert retval == 0
        prefix = builddir.join(test)
        cpyver = '%d.%d' % CPYTHON_VERSION[:2]
        assert prefix.join('lib-python', cpyver, 'test').check()
        assert prefix.join(self.exe_name_in_archive).check()
        assert prefix.join('lib_pypy', 'syslog.py').check()
        assert not prefix.join('lib_pypy', 'py').check()
        assert not prefix.join('lib_pypy', 'ctypes_configure').check()
        assert prefix.join('LICENSE').check()
        assert prefix.join('README.rst').check()
        if package.USE_ZIPFILE_MODULE:
            zh = zipfile.ZipFile(str(builddir.join('%s.zip' % test)))
            assert zh.open('%s/lib_pypy/syslog.py' % test)
        else:
            th = tarfile.open(str(builddir.join('%s.tar.gz' % test)))
            syslog = th.getmember('%s/lib_pypy/syslog.py' % (test))
            exe = th.getmember('%s/%s' % (test, self.exe_name_in_archive))
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

    def test_options(self, test='testoptions'):
        builddir = udir.ensure("build", dir=True)
        retval, builddir = package.package(
            '--without-cffi', '--builddir', str(builddir),
            '--archive-name', test,
            '--rename_pypy_c', self.rename_pypy_c,
            _fake=True)

    def test_with_zipfile_module(self):
        prev = package.USE_ZIPFILE_MODULE
        try:
            package.USE_ZIPFILE_MODULE = True
            self.test_dir_structure(test='testzipfile')
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

def test_codesign_macho_files(tmpdir):
    if sys.platform != 'darwin':
        py.test.skip('code signatures are a darwin thing')
    import shutil, subprocess
    def verify(path):
        with open(os.devnull, 'wb') as devnull:
            return subprocess.call(['codesign', '--verify', '--strict', path],
                                   stdout=devnull, stderr=devnull) == 0
    #
    work = str(tmpdir)
    # a Mach-O to repair, plus a text file and a symlink to be left alone
    dylib = os.path.join(work, 'libpypy-c.dylib')
    shutil.copy(sys.executable, dylib)
    tmpdir.join('notes.txt').write('not a mach-o\n')
    os.symlink('libpypy-c.dylib', os.path.join(work, 'link.dylib'))
    #
    assert list(package.find_macho_files(work)) == [dylib]
    # smartstrip() and make_portable() rewrite the binary in place, which
    # leaves the signature covering content that is no longer there.  Flipping
    # a byte in the middle of the file has the same effect and does not depend
    # on what install_name_tool happens to repair on its own.
    os.chmod(dylib, 0o755)
    with open(dylib, 'r+b') as fid:
        middle = os.path.getsize(dylib) // 2
        fid.seek(middle)
        flipped = bytearray(fid.read(1))
        flipped[0] ^= 0xff
        fid.seek(middle)
        fid.write(bytes(flipped))
    assert not verify(dylib)
    #
    package.codesign_macho_files(work)
    assert verify(dylib)
    # and it is a no-op the second time around
    package.codesign_macho_files(work)
    assert verify(dylib)

def test_generate_license():
    py.test.skip('generation of license from platform documentation is disabled')
    from os.path import dirname, abspath, join, exists
    class Options(object):
        pass
    options = Options()
    basedir = dirname(dirname(dirname(dirname(dirname(abspath(__file__))))))
    options.no_tk = False
    if sys.platform == 'win32':
        for p in [join(basedir, r'..\..\..\local'), #buildbot
                  join(basedir, r'..\local')]: # pypy/doc/windows.rst
            if exists(p):
                license_base = p
                break
        else:
            license_base = 'unkown'
        options.license_base = license_base
    else:
        options.license_base = '/usr/share/doc'
    license = package.generate_license(py.path.local(basedir), options)
    assert 'bzip2' in license
    assert 'openssl' in license
    assert 'Tcl' in license

