import os, sys
import tempfile

# Monkeypatch & hacks to let ctypes.tests import.
# This should be removed at some point.
sys.getrefcount = None
import _ctypes
_ctypes.PyObj_FromPtr = None
del _ctypes

def compile_shared():
    """Compile '_ctypes_test.c' into an extension module, and import it
    """
    thisdir = os.path.dirname(__file__)
    output_dir = tempfile.mkdtemp()

    from distutils.ccompiler import new_compiler
    compiler = new_compiler()
    compiler.output_dir = output_dir

    # Compile .c file
    include_dir = os.path.join(thisdir, '..', 'include')
    res = compiler.compile([os.path.join(thisdir, '_ctypes_test.c')],
                           include_dirs=[include_dir])
    object_filename = res[0]

    # set link options
    if sys.platform == 'win32':
        output_filename = '_ctypes_test.pyd'
        # XXX libpypy-c.lib is currently not installed automatically
        library = os.path.join(thisdir, '..', 'include', 'libpypy-c')
        libraries = [library, 'oleaut32']
        extra_ldargs = ['/MANIFEST'] # needed for VC10
    else:
        output_filename = '_ctypes_test.so'
        libraries = []
        extra_ldargs = []

    # link the dynamic library
    compiler.link_shared_object(
        [object_filename],
        output_filename,
        libraries=libraries,
        extra_preargs=extra_ldargs)

    # Now import the newly created library, it will replace our module in sys.modules
    import imp
    fp, filename, description = imp.find_module('_ctypes_test', path=[output_dir])
    imp.load_module('_ctypes_test', fp, filename, description)

compile_shared()
