import os, sys
import tempfile

def compile_shared():
    """Compile '_testcapi.c' into an extension module, and import it
    """
    thisdir = os.path.dirname(__file__)
    output_dir = tempfile.mkdtemp()

    from distutils.ccompiler import new_compiler
    from distutils import sysconfig

    compiler = new_compiler()
    compiler.output_dir = output_dir

    # Compile .c file
    include_dir = os.path.join(thisdir, '..', 'include')
    if sys.platform == 'win32':
        ccflags = []
    else:
        ccflags = ['-fPIC', '-Wimplicit-function-declaration']
    res = compiler.compile([os.path.join(thisdir, '_testcapimodule.c')],
                           include_dirs=[include_dir],
                           extra_preargs=ccflags)
    object_filename = res[0]

    # set link options
    output_filename = '_testcapi' + sysconfig.get_config_var('SO')
    if sys.platform == 'win32':
        # XXX libpypy-c.lib is currently not installed automatically
        library = os.path.join(thisdir, '..', 'include', 'libpypy-c')
        libraries = [library, 'oleaut32']
        extra_ldargs = ['/MANIFEST',  # needed for VC10
                        '/EXPORT:init_testcapi']
    else:
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
    fp, filename, description = imp.find_module('_testcapi', path=[output_dir])
    imp.load_module('_testcapi', fp, filename, description)

compile_shared()
