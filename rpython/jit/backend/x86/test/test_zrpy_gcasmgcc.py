import py
from rpython.jit.backend.llsupport.test.zrpy_gc_test import CompileFrameworkTests
from rpython.translator.platform import platform as compiler

if compiler.name == 'msvc':
    py.test.skip('asmgcc buggy on msvc')

class TestAsmGcc(CompileFrameworkTests):
    gcrootfinder = "asmgcc"
