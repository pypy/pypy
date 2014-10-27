import py, pytest
import sys

def pytest_ignore_collect(path):
    if '__pypy__' not in sys.builtin_module_names:
        return True

def compile_so_file():
    from rpython.translator.platform import platform
    from rpython.translator.tool.cbuild import ExternalCompilationInfo
    from rpython.translator import cdir
    udir = pytest.ensuretemp('_ctypes_test')
    cfile = py.path.local(__file__).dirpath().join("_ctypes_test.c")

    if sys.platform == 'win32':
        libraries = ['oleaut32']
    else:
        libraries = []
    eci = ExternalCompilationInfo(libraries=libraries,
                                  include_dirs=[cdir])

    return platform.compile([cfile], eci, str(udir.join('_ctypes_test')),
                            standalone=False)

# we need to run after the "tmpdir" plugin which installs pytest.ensuretemp
@pytest.mark.trylast
def pytest_configure(config):
    global sofile
    sofile = compile_so_file()
