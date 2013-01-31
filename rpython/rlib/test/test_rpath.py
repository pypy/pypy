import py
import os
from rpython.rlib import rpath

IS_WINDOWS = os.name == 'nt'

def test_rabspath_relative(tmpdir):
    tmpdir.chdir()
    assert rpath.rabspath('foo') == os.path.realpath(tmpdir.join('foo'))

@py.test.mark.skipif("IS_WINDOWS")
def test_rabspath_absolute_posix():
    assert rpath.rabspath('/foo') == '/foo'

@py.test.mark.skipif("not IS_WINDOWS")
def test_rabspath_absolute_nt():
    curdrive, _ = os.path.splitdrive(os.getcwd())
    assert rpath.rabspath('\\foo') == '%s\\foo' % curdrive
