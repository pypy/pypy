import os, sys, imp
import tempfile

def _get_c_extension_suffix():
    for ext, mod, typ in imp.get_suffixes():
        if typ == imp.C_EXTENSION:
            return ext


def compile_shared(csource, modulename, output_dir=None):
    """Compile '_testcapi.c' or '_ctypes_test.c' into an extension module,
    and import it.
    """
    thisdir = os.path.dirname(__file__)
    if output_dir is None:
        output_dir = tempfile.mkdtemp()

    from distutils.ccompiler import new_compiler

    compiler = new_compiler()
    compiler.output_dir = output_dir

    # Compile .c file
    include_dir = os.path.join(thisdir, '..', 'include')
    if sys.platform == 'win32':
        ccflags = ['-D_CRT_SECURE_NO_WARNINGS']
    else:
        ccflags = ['-fPIC', '-Wimplicit-function-declaration']
    res = compiler.compile([os.path.join(thisdir, csource)],
                           include_dirs=[include_dir],
                           extra_preargs=ccflags)
    object_filename = res[0]

    # set link options
    output_filename = modulename + _get_c_extension_suffix()
    if sys.platform == 'win32':
        # XXX pyconfig.h uses a pragma to link to the import library,
        #     which is currently python27.lib
        library = os.path.join(thisdir, '..', 'include', 'python27')
        if not os.path.exists(library + '.lib'):
            # For a local translation or nightly build
            library = os.path.join(thisdir, '..', 'pypy', 'goal', 'python27')
        assert os.path.exists(library + '.lib'),'Could not find import library "%s"' % library
        libraries = [library, 'oleaut32']
        extra_ldargs = ['/MANIFEST',  # needed for VC10
                        '/EXPORT:init' + modulename]
    else:
        libraries = []
        extra_ldargs = []

    # link the dynamic library
    compiler.link_shared_object(
        [object_filename],
        output_filename,
        libraries=libraries,
        extra_preargs=extra_ldargs)

    # Now import the newly created library, it will replace the original
    # module in sys.modules
    fp, filename, description = imp.find_module(modulename, path=[output_dir])
    imp.load_module(modulename, fp, filename, description)
