import py
import os
from rpython.rlib import rpath

IS_WINDOWS = os.name == 'nt'

def test_rabspath_relative(tmpdir):
    tmpdir.chdir()
    assert rpath.rabspath('foo') == os.path.realpath(str(tmpdir.join('foo')))

@py.test.mark.skipif("IS_WINDOWS")
def test_rabspath_absolute_posix():
    assert rpath.rabspath('/foo') == '/foo'

@py.test.mark.skipif("IS_WINDOWS")
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

@py.test.mark.skipif("not IS_WINDOWS")
def test_rabspath_absolute_nt():
    curdrive, _ = os.path.splitdrive(os.getcwd())
    assert rpath.rabspath('\\foo') == '%s\\foo' % curdrive
