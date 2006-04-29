"""
Test errno.
"""

import py
import sys, errno
import pypy.rpython.rctypes.implementation
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy import conftest
from pypy.rpython.rctypes import aerrno
from pypy.rpython.rctypes.test.test_rfunc import mylib

from ctypes import c_char_p, c_int


if sys.platform == 'win32':
    py.test.skip("Unix only for now")

open = mylib.open
open.argtypes = [c_char_p, c_int, c_int]
open.restype = c_int
def ll_open(p, flags, mode):
    s = ''
    i = 0
    while p[i] != '\x00':
        s += p[i]
        i += 1
    return open(s, flags, mode)
open.llinterp_friendly_version = ll_open
open.includes = ('fcntl.h',)


def test_open():
    if sys.platform == 'win32':
        py.test.skip("Unix only")
    open = mylib.open
    fd = open("/_rctypes_test_rfunc/this/directory/does/not/exist/at/all!",
              0, 0)
    result = aerrno.geterrno()
    assert fd == -1
    assert result == errno.ENOENT

class Test_annotation:
    def test_annotate_geterrno(self):
        def f():
            return aerrno.geterrno()
        a = RPythonAnnotator()
        s = a.build_types(f, [])
        if conftest.option.view:
            a.translator.view()
        assert s.knowntype == int

class Test_specialization:
    def test_specialize_geterrno(self):
        if sys.platform == 'win32':
            py.test.skip("Unix only")
        open = mylib.open
        open.argtypes = [c_char_p, c_int, c_int]
        open.restype = c_int
        def func():
            fd = open(
                "/_rctypes_test_rfunc/this/directory/does/not/exist/at/all!",
                0, 0)
            return fd, aerrno.geterrno()

        res = interpret(func, [])
        assert res.item0 == -1
        # the following doesn't work because the llinterp calls many C library
        # functions between open() and geterrno()
        ##assert res.item1 == errno.ENOENT

class Test_compile:
    def test_compile_geterrno(self):
        if sys.platform == 'win32':
            py.test.skip("Unix only")
        open = mylib.open
        open.argtypes = [c_char_p, c_int, c_int]
        open.restype = c_int
        def func():
            fd = open(
                "/_rctypes_test_rfunc/this/directory/does/not/exist/at/all!",
                0, 0)
            return fd, aerrno.geterrno()

        fn = compile(func, [])
        fd, result = fn()
        assert fd == -1
        assert result == errno.ENOENT
