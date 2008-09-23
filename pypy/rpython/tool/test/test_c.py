
import os
import sys
from pypy.tool.udir import udir
from distutils import ccompiler
import py
import ctypes

c_source = """
void *int_to_void_p(int arg) {}

struct random_strucutre {
  int one;
  int *two;
};

struct random_structure* int_int_to_struct_p(int one, int two) {}
"""

class TestBasic:
    def setup_class(cls):
        compiler = ccompiler.new_compiler()
        c_file = udir.join('rffilib.c')
        c_file.write(c_source)

        if sys.platform == 'win32':
            ccflags = []
            o_file = 'rffilib.obj'
            so_file = 'rffi.dll'
        else:
            ccflags = ['-fPIC']
            o_file = 'rffilib.o' 
            so_file = 'librffi.so'

        rootdir = os.path.splitdrive(str(udir))[0] + '/'
        compiler.compile([str(c_file)], output_dir=rootdir,
                         extra_preargs=ccflags)

        compiler.link_shared_lib([str(udir.join(o_file))],
                                 'rffi', output_dir=str(udir),
                                 export_symbols = ['int_int_to_struct_p',
                                                   'int_to_void_p'])
        cls.lib = ctypes.CDLL(str(udir.join(so_file)))

    def test_basic(self):
        assert self.lib
        
