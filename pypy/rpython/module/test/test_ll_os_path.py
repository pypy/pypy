import py

import os

from pypy.tool.pytest.modcheck import skipimporterror
skipimporterror("ctypes")

from pypy.rpython.lltypesystem.module.ll_os_path import Implementation as impl
from pypy.rpython.module.support import ll_strcpy
from pypy.rpython.test.test_llinterp import interpret
from pypy.tool.udir import udir

def test_exists():
    filename = impl.to_rstr(str(py.magic.autopath()))
    assert impl.ll_os_path_exists(filename) == True
    assert not impl.ll_os_path_exists(impl.to_rstr(
        "strange_filename_that_looks_improbable.sde"))

def test_posixpath():
    import posixpath
    def f():
        assert posixpath.join("/foo", "bar") == "/foo/bar"
        assert posixpath.join("/foo", "spam/egg") == "/foo/spam/egg"
        assert posixpath.join("/foo", "/bar") == "/bar"
    interpret(f, [])

def test_ntpath():
    import ntpath
    def f():
        assert ntpath.join("\\foo", "bar") == "\\foo\\bar"
        assert ntpath.join("c:\\foo", "spam\\egg") == "c:\\foo\\spam\\egg"
        assert ntpath.join("c:\\foo", "d:\\bar") == "d:\\bar"
    interpret(f, [])

def test_isdir():
    import py; py.test.skip("XXX cannot run os.stat() on the llinterp yet")
    s = str(udir.join('test_isdir'))
    def f():
        return os.path.isdir(s)
    res = interpret(f, [])
    assert res == os.path.isdir(s)
    os.mkdir(s)
    res = interpret(f, [])
    assert res is True
