import os, sys
import pytest, py
import re

PY2 = sys.version_info[0] == 2

r_marker_init = re.compile(r"\s*@INIT\s*$")
r_marker_export = re.compile(r"\s*@EXPORT\s+(\w+)\s+(.*)\s*$")

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
            if not ml_flags.startswith('HPy_'):
                # this is a legacy function: add a cast to (HPyMeth) to
                # silence warnings
                cast = '(HPyMeth)'
            else:
                cast = ''
            method_table.append('{"%s", %s%s, %s, NULL},' % (
                    ml_name, cast, ml_name, ml_flags))
            continue

        expanded_lines.append(line)
    return '\n'.join(expanded_lines)


class Spec(object):
    def __init__(self, name, origin):
        self.name = name
        self.origin = origin


class ExtensionCompiler:
    def __init__(self, tmpdir, abimode, include_dir, compiler_verbose=False,
                 cpython_include_dirs=None):
        """
        cpython_include_dirs is a list of dirs where to find Python.h. If None,
        _build will automatically use the include dirs provided by distutils.
        Alternate Python implementations can use this to #include their own
        version of Python.h
        """
        self.tmpdir = tmpdir
        self.abimode = abimode
        self.include_dir = include_dir
        self.universal_mode = self.abimode == 'universal'
        self.compiler_verbose = compiler_verbose
        self.cpython_include_dirs = cpython_include_dirs

    def _expand(self, name, template):
        source = expand_template(template, name)
        filename = self.tmpdir.join(name + '.c')
        if PY2:
            # this code is used also by pypy tests, which run on python2. In
            # this case, we need to write as binary, because source is
            # "bytes". If we don't and source contains a non-ascii char, we
            # get an UnicodeDecodeError
            filename.write(source, mode='wb')
        else:
            filename.write(source)
        return str(filename)

    def compile_module(self, main_template, name, extra_templates):
        """
        Create and compile a HPy module from the template
        """
        filename = self._expand(name, main_template)
        sources = [
            str(py.path.local(__file__).dirpath().dirpath().join(
                'hpy/devel/src/runtime/argparse.c')),
        ]
        for i, template in enumerate(extra_templates):
            extra_filename = self._expand('extmod_%d' % i, template)
            sources.append(extra_filename)
        #
        ext = get_extension(str(filename), name,
                            sources=sources,
                            include_dirs=[self.include_dir],
                            extra_compile_args=['-Wfatal-errors', '-g', '-O0'],
                            extra_link_args=['-g'])
        so_filename = c_compile(str(self.tmpdir), ext,
                                compiler_verbose=self.compiler_verbose,
                                universal_mode=self.universal_mode,
                                cpython_include_dirs=self.cpython_include_dirs)
        return so_filename

    def make_module(self, main_template, name, extra_templates):
        """
        Compile&load a modulo into memory. This is NOT a proper import: e.g. the module
        is not put into sys.modules
        """
        so_filename = self.compile_module(main_template, name, extra_templates)
        if self.universal_mode:
            return self.load_universal_module(name, so_filename)
        else:
            return self.load_cython_module(name, so_filename)

    def load_universal_module(self, name, so_filename):
        assert self.abimode == 'universal'
        import hpy.universal
        spec = Spec(name, so_filename)
        return hpy.universal.load_from_spec(spec)

    def load_cython_module(self, name, so_filename):
        assert self.abimode == 'cpython'
        # we've got a normal CPython module compiled with the CPython API/ABI,
        # let's load it normally. It is important to do the imports only here,
        # because this file will be imported also by PyPy tests which runs on
        # Python2
        import importlib.util
        from importlib.machinery import ExtensionFileLoader
        spec = importlib.util.spec_from_file_location(name, so_filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


@pytest.mark.usefixtures('initargs')
class HPyTest:
    @pytest.fixture()
    def initargs(self, compiler):
        # compiler is a fixture defined in conftest
        self.compiler = compiler

    def make_module(self, source_template, name='mytest', extra_templates=()):
        return self.compiler.make_module(source_template, name, extra_templates)

    def should_check_refcount(self):
        # defaults to True on CPython, but is set to False by e.g. PyPy
        return True


# the few functions below are copied and adapted from cffi/ffiplatform.py

def get_extension(srcfilename, modname, sources=(), **kwds):
    from distutils.core import Extension
    allsources = [srcfilename]
    for src in sources:
        allsources.append(os.path.normpath(src))
    return Extension(name=modname, sources=allsources, **kwds)

def c_compile(tmpdir, ext, compiler_verbose=0, debug=None,
              universal_mode=False, cpython_include_dirs=None):
    """Compile a C extension module using distutils."""
    saved_environ = os.environ.copy()
    try:
        outputfilename = _build(tmpdir, ext, compiler_verbose, debug,
                                universal_mode, cpython_include_dirs)
        outputfilename = os.path.abspath(outputfilename)
    finally:
        # workaround for a distutils bugs where some env vars can
        # become longer and longer every time it is used
        for key, value in saved_environ.items():
            if os.environ.get(key) != value:
                os.environ[key] = value
    return outputfilename

def _build(tmpdir, ext, compiler_verbose=0, debug=None, universal_mode=False,
           cpython_include_dirs=None):
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
            if cpython_include_dirs is None:
                cpython_include_dirs = cmd_obj.include_dirs
            soname = _build_universal(tmpdir, ext, cpython_include_dirs)
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
                               include_dirs=include_dirs,
                               extra_preargs=ext.extra_compile_args)

    filename = ext.name + '.hpy.so'
    compiler.link(compiler.SHARED_LIBRARY,
                  objects,
                  filename,
                  tmpdir,
                  extra_preargs=ext.extra_link_args,
                  # export_symbols=...
                  )
    return os.path.join(tmpdir, filename)
