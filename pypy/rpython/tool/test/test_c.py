
import os
import sys
from pypy.tool.udir import udir
from distutils import ccompiler
import py
import ctypes

c_source = """
void *int_to_void_p(int arg) {}
"""

class TestBasic:
    def setup_class(cls):
        compiler = ccompiler.new_compiler()
        c_file = udir.join('rffilib.c')
        c_file.write(c_source)
        compiler.compile([str(c_file)], output_dir='/')
        compiler.link_shared_lib([str(udir.join('rffilib.o'))],
                                  'rffi', output_dir=str(udir))
        cls.lib = ctypes.CDLL(str(udir.join('librffi.so')))

    def test_basic(self):
        assert self.lib
        
