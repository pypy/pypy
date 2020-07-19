import os, sys
import pytest, py
import re
import textwrap

PY2 = sys.version_info[0] == 2

def reindent(s, indent):
    s = textwrap.dedent(s)
    return textwrap.indent(s, ' '*indent)

class ExtensionTemplate(object):

    INIT_TEMPLATE = textwrap.dedent("""
    static HPyModuleDef moduledef = {
        HPyModuleDef_HEAD_INIT,
        .m_name = "%(name)s",
        .m_doc = "some test for hpy",
        .m_size = -1,
        .legacy_methods = %(legacy_methods)s,
        .defines = {
            %(defines)s
            NULL
        }
    };

    HPy_MODINIT(%(name)s)
    static HPy init_%(name)s_impl(HPyContext ctx)
    {
        HPy m;
        m = HPyModule_Create(ctx, &moduledef);
        if (HPy_IsNull(m))
            return HPy_NULL;
        %(init_types)s
        return m;
    }
    """)

    r_marker = re.compile(r"^\s*@([A-Z_]+)(\(.*\))?$")

    def __init__(self, src, name):
        self.src = textwrap.dedent(src)
        self.name = name
        self.defines_table = None
        self.legacy_methods = 'NULL'
        self.type_table = None

    def expand(self):
        self.defines_table = []
        self.type_table = []
        self.output = ['#include <hpy.h>']
        for line in self.src.split('\n'):
            match = self.r_marker.match(line)
            if match:
                name, args = self.parse_marker(match)
                meth = getattr(self, name)
                meth(*args)
            else:
                self.output.append(line)
        return '\n'.join(self.output)

    def parse_marker(self, match):
        name = match.group(1)
        args = match.group(2)
        if args is None:
            args = ()
        else:
            assert args[0] == '('
            assert args[-1] == ')'
            args = args[1:-1].split(',')
            args = [x.strip() for x in args]
        return name, args

    def INIT(self):
        if self.type_table:
            init_types = '\n'.join(self.type_table)
        else:
            init_types = ''

        exp = self.INIT_TEMPLATE % {
            'legacy_methods': self.legacy_methods,
            'defines': '\n        '.join(self.defines_table),
            'init_types': init_types,
            'name': self.name}
        self.output.append(exp)
        # make sure that we don't fill the tables any more
        self.defines_table = None
        self.type_table = None

    def EXPORT(self, meth):
        self.defines_table.append('&%s,' % meth)

    def EXPORT_LEGACY(self, pymethoddef):
        self.legacy_methods = pymethoddef

    def EXPORT_TYPE(self, name, spec):
        i = len(self.type_table)
        src = """
            HPy {h} = HPyType_FromSpec(ctx, &{spec});
            if (HPy_IsNull({h}))
                return HPy_NULL;
            if (HPy_SetAttr_s(ctx, m, {name}, {h}) != 0)
                return HPy_NULL;
            """
        src = reindent(src, 4)
        self.type_table.append(src.format(
            h = 'h_type_%d' % i,
            name = name,
            spec = spec))

def expand_template(template, name):
    return ExtensionTemplate(template, name).expand()


class Spec(object):
    def __init__(self, name, origin):
        self.name = name
        self.origin = origin


class ExtensionCompiler:
    def __init__(self, tmpdir, abimode, base_dir, compiler_verbose=False,
                 cpython_include_dirs=None):
        """
        base_dir is the directory where to find include/, runtime/src,
        etc. Usually it will point to hpy/devel/, but alternate implementation
        can point to their own place.

        cpython_include_dirs is a list of dirs where to find Python.h. If None,
        _build will automatically use the include dirs provided by distutils.
        Alternate Python implementations can use this to #include their own
        version of Python.h
        """
        self.tmpdir = tmpdir
        self.abimode = abimode
        self.base_dir = py.path.local(base_dir)
        self.include_dir = self.base_dir.join('include')
        self.src_dir = self.base_dir.join('src', 'runtime')
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
        #
        # XXX: we should probably use hpy.devel.get_sources() to get all the
        # needed files
        sources = [
            str(self.src_dir.join('argparse.c')),
        ]
        if self.abimode == 'cpython':
            sources.append(str(self.src_dir.join('ctx_module.c')))
            sources.append(str(self.src_dir.join('ctx_type.c')))
        #
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
        return sys.implementation.name == 'cpython'


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
