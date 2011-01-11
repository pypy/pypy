import py
import sys

def pytest_ignore_collect(path):
    if '__pypy__' not in sys.builtin_module_names:
        return True

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
