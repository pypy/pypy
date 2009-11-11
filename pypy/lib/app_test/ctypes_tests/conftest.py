import py
import sys

class Directory(py.test.collect.Directory):
    def collect(self):
        if '__pypy__' not in sys.builtin_module_names:
            py.test.skip("these tests are meant to be run on top of pypy-c")
        return super(Directory, self).collect()

def compile_so_file():
    from pypy.translator.platform import platform
    from pypy.translator.tool.cbuild import ExternalCompilationInfo
    udir = py.test.ensuretemp('_ctypes_test')
    cfile = py.path.local(__file__).dirpath().join("_ctypes_test.c")

    if sys.platform == 'win32':
        libraries = ['oleaut32']
    else:
        libraries = []
    eci = ExternalCompilationInfo(libraries=libraries)

    return platform.compile([cfile], eci, str(udir.join('_ctypes_test')),
                            standalone=False)

def pytest_configure(config):
    global sofile
    sofile = compile_so_file()
