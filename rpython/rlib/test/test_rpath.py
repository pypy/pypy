import py
import os
from rpython.rlib import rpath

def test_rabspath_relative(tmpdir):
    tmpdir.chdir()
    assert rpath.rabspath('foo') == os.path.realpath(str(tmpdir.join('foo')))

def test_rabspath_absolute_posix():
    assert rpath._posix_rabspath('/foo') == '/foo'

@py.test.mark.skipif("os.name == 'nt'")
def test_missing_current_dir(tmpdir):
    tmpdir1 = str(tmpdir) + '/temporary_removed'
    curdir1 = os.getcwd()
    try:
        os.mkdir(tmpdir1)
        os.chdir(tmpdir1)
        os.rmdir(tmpdir1)
        result = rpath.rabspath('.')
    finally:
        os.chdir(curdir1)
    assert result == '.'

def test_rsplitdrive_nt():
    assert rpath._nt_rsplitdrive('D:\\FOO/BAR') == ('D:', '\\FOO/BAR')
    assert rpath._nt_rsplitdrive('//') == ('', '//')

@py.test.mark.skipif("os.name != 'nt'")
def test_rabspath_absolute_nt():
    curdrive = _ = rpath._nt_rsplitdrive(os.getcwd())
    assert len(curdrive) == 2 and curdrive[1] == ':'
    assert rpath.rabspath('\\foo') == '%s\\foo' % curdrive

def test_risabs_posix():
    assert rpath._posix_risabs('/foo/bar')
    assert not rpath._posix_risabs('foo/bar')
    assert not rpath._posix_risabs('\\foo\\bar')
    assert not rpath._posix_risabs('C:\\foo\\bar')

def test_risabs_nt():
    assert rpath._nt_risabs('/foo/bar')
    assert not rpath._nt_risabs('foo/bar')
    assert rpath._nt_risabs('\\foo\\bar')
    assert rpath._nt_risabs('C:\\FOO')
    assert not rpath._nt_risabs('C:FOO')

def test_risdir(tmpdir):
    assert rpath.risdir(tmpdir)
    assert not rpath.risdir('_some_non_existant_file_')
    assert not rpath.risdir(os.path.join(tmpdir, '_some_non_existant_file_'))
