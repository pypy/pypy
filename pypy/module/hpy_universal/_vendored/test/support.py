import os, sys
import pytest
import re
#import importlib.util
#from importlib.machinery import ExtensionFileLoader

THIS_DIR = os.path.dirname(__file__)
INCLUDE_DIR = os.path.join(THIS_DIR, '../hpy-api/include')


r_marker_init = re.compile(r"\s*@INIT\s*$")
r_marker_export = re.compile(r"\s*@EXPORT\s+(\w+)\s+(METH_\w+)\s*$")

INIT_TEMPLATE = """
static HPyMethodDef MyTestMethods[] = {
    %(methods)s
    {NULL, NULL, 0, NULL}
};

static HPyModuleDef moduledef = {
    HPyModuleDef_HEAD_INIT,
    .m_name = "%(name)s",
    .m_doc = "some test for hpy",
    .m_size = -1,
    .m_methods = MyTestMethods
};

HPy_MODINIT(%(name)s)
static HPy init_%(name)s_impl(HPyContext ctx)
{
    HPy m;
    m = HPyModule_Create(ctx, &moduledef);
    if (HPy_IsNull(m))
        return HPy_NULL;
    return m;
}
"""


def expand_template(source_template, name):
    method_table = []
    expanded_lines = ['#include <hpy.h>']
    for line in source_template.split('\n'):
        match = r_marker_init.match(line)
        if match:
            exp = INIT_TEMPLATE % {
                'methods': '\n    '.join(method_table),
                'name': name}
            method_table = None   # don't fill it any more
            expanded_lines.append(exp)
            continue

        match = r_marker_export.match(line)
        if match:
            ml_name, ml_flags = match.group(1), match.group(2)
            method_table.append('{"%s", %s, %s, NULL},' % (
                ml_name, ml_name, ml_flags))
            continue

        expanded_lines.append(line)
    return '\n'.join(expanded_lines)


#class HPyLoader(ExtensionFileLoader):
#    def create_module(self, spec):
#        import hpy_universal
#        return hpy_universal.load(spec.origin, "HPyInit_" + spec.name)

class ExtensionCompiler:
    def __init__(self, tmpdir, abimode):
        self.tmpdir = tmpdir
        self.abimode = abimode

    def make_module(self, source_template, name):
        universal_mode = self.abimode == 'universal'
        source = expand_template(source_template, name)
        filename = self.tmpdir.join(name + '.c')
        filename.write(source)
        #
        ext = get_extension(str(filename), name, include_dirs=[INCLUDE_DIR],
                            extra_compile_args=['-Wfatal-errors'])
        so_filename = c_compile(str(self.tmpdir), ext, compiler_verbose=False,
                                universal_mode=universal_mode)
        #
        if universal_mode:
            loader = HPyLoader(name, so_filename)
            spec = importlib.util.spec_from_loader(name, loader)
        else:
            spec = importlib.util.spec_from_file_location(name, so_filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


@pytest.mark.usefixtures('initargs')
class HPyTest:
    @pytest.fixture()
    def initargs(self, compiler):
        self.compiler = compiler

    def make_module(self, source_template, name='mytest'):
        return self.compiler.make_module(source_template, name)


# the few functions below are copied and adapted from cffi/ffiplatform.py

def get_extension(srcfilename, modname, sources=(), **kwds):
    from distutils.core import Extension
    allsources = [srcfilename]
    for src in sources:
        allsources.append(os.path.normpath(src))
    return Extension(name=modname, sources=allsources, **kwds)

def c_compile(tmpdir, ext, compiler_verbose=0, debug=None,
              universal_mode=False):
    """Compile a C extension module using distutils."""

    saved_environ = os.environ.copy()
    try:
        outputfilename = _build(tmpdir, ext, compiler_verbose, debug,
                                universal_mode)
        outputfilename = os.path.abspath(outputfilename)
    finally:
        # workaround for a distutils bugs where some env vars can
        # become longer and longer every time it is used
        for key, value in saved_environ.items():
            if os.environ.get(key) != value:
                os.environ[key] = value
    return outputfilename

def _build(tmpdir, ext, compiler_verbose=0, debug=None, universal_mode=False):
    # XXX compact but horrible :-(
    from distutils.core import Distribution
    import distutils.errors, distutils.log
    #
    dist = Distribution({'ext_modules': [ext]})
    dist.parse_config_files()
    options = dist.get_option_dict('build_ext')
    if debug is None:
        debug = sys.flags.debug
    options['debug'] = ('ffiplatform', debug)
    options['force'] = ('ffiplatform', True)
    options['build_lib'] = ('ffiplatform', tmpdir)
    options['build_temp'] = ('ffiplatform', tmpdir)
    #
    old_level = distutils.log.set_threshold(0) or 0
    try:
        distutils.log.set_verbosity(compiler_verbose)
        if universal_mode:
            cmd_obj = dist.get_command_obj('build_ext')
            cmd_obj.finalize_options()
            soname = _build_universal(tmpdir, ext, cmd_obj.include_dirs)
        else:
            dist.run_command('build_ext')
            cmd_obj = dist.get_command_obj('build_ext')
            [soname] = cmd_obj.get_outputs()
    finally:
        distutils.log.set_threshold(old_level)
    #
    return soname

def _build_universal(tmpdir, ext, cpython_include_dirs):
    from distutils.ccompiler import new_compiler, get_default_compiler
    from distutils.sysconfig import customize_compiler

    compiler = new_compiler(get_default_compiler())
    customize_compiler(compiler)

    include_dirs = ext.include_dirs + cpython_include_dirs
    objects = compiler.compile(ext.sources,
                               output_dir=tmpdir,
                               macros=[('HPY_UNIVERSAL_ABI', None)],
                               include_dirs=include_dirs)

    filename = ext.name + '.hpy.so'
    compiler.link(compiler.SHARED_LIBRARY,
                  objects,
                  filename,
                  tmpdir
                  # export_symbols=...
                  )
    return os.path.join(tmpdir, filename)
