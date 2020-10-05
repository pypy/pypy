import os, sys
import pytest, py
import re
import textwrap

PY2 = sys.version_info[0] == 2

def reindent(s, indent):
    s = textwrap.dedent(s)
    return ''.join(' '*indent + line if line.strip() else line
        for line in s.splitlines(True))

class DefaultExtensionTemplate(object):

    INIT_TEMPLATE = textwrap.dedent("""
    static HPyDef *moduledefs[] = {
        %(defines)s
        NULL
    };
    static HPyModuleDef moduledef = {
        HPyModuleDef_HEAD_INIT,
        .m_name = "%(name)s",
        .m_doc = "some test for hpy",
        .m_size = -1,
        .legacy_methods = %(legacy_methods)s,
        .defines = moduledefs
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

    r_marker = re.compile(r"^\s*@([A-Za-z_]+)(\(.*\))?$")

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
                out = meth(*args)
                if out is not None:
                    out = textwrap.dedent(out)
                    self.output.append(out)
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
            HPy {h} = HPyType_FromSpec(ctx, &{spec}, NULL);
            if (HPy_IsNull({h}))
                return HPy_NULL;
            if (HPy_SetAttr_s(ctx, m, {name}, {h}) != 0)
                return HPy_NULL;
            HPy_Close(ctx, {h});
            """
        src = reindent(src, 4)
        self.type_table.append(src.format(
            h = 'h_type_%d' % i,
            name = name,
            spec = spec))

    def EXTRA_INIT_FUNC(self, func):
        src = """
            {func}(ctx, m);
            if (HPyErr_Occurred(ctx))
                return HPy_NULL;
            """
        src = reindent(src, 4)
        self.type_table.append(src.format(func=func))


class Spec(object):
    def __init__(self, name, origin):
        self.name = name
        self.origin = origin


class ExtensionCompiler:
    def __init__(self, tmpdir, hpy_devel, hpy_abi, compiler_verbose=False,
                 extra_include_dirs=None):
        """
        hpy_devel is an instance of HPyDevel which specifies where to find
        include/, runtime/src, etc. Usually it will point to hpy/devel/, but
        alternate implementations can point to their own place (e.g. pypy puts
        it into pypy/module/_hpy_universal/_vendored)

        extra_include_dirs is a list of include dirs which is put BEFORE all
        others. By default it is empty, but it is used e.g. by PyPy to make
        sure that #include <Python.h> picks its own version, instead of the
        system-wide one.
        """
        self.tmpdir = tmpdir
        self.hpy_devel = hpy_devel
        self.hpy_abi = hpy_abi
        self.compiler_verbose = compiler_verbose
        self.extra_include_dirs = extra_include_dirs

    def _expand(self, ExtensionTemplate, name, template):
        source = ExtensionTemplate(template, name).expand()
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

    def compile_module(self, ExtensionTemplate, main_src, name, extra_sources):
        """
        Create and compile a HPy module from the template
        """
        from distutils.core import Extension
        filename = self._expand(ExtensionTemplate, name, main_src)
        sources = [str(filename)]
        for i, src in enumerate(extra_sources):
            extra_filename = self._expand(ExtensionTemplate, 'extmod_%d' % i, src)
            sources.append(extra_filename)
        #
        compile_args = [
            '-g', '-O0',
            '-Wfatal-errors',    # stop after one error (unrelated to warnings)
            '-Werror',           # turn warnings into errors (all, for now)
        ]
        link_args = [
            '-g',
        ]
        #
        ext = Extension(
            name,
            sources=sources,
            include_dirs=self.extra_include_dirs,
            extra_compile_args=compile_args,
            extra_link_args=link_args)

        so_filename = c_compile(str(self.tmpdir), ext,
                                hpy_devel=self.hpy_devel,
                                hpy_abi=self.hpy_abi,
                                compiler_verbose=self.compiler_verbose)
        return so_filename

    def make_module(self, ExtensionTemplate, main_src, name, extra_sources):
        """
        Compile&load a modulo into memory. This is NOT a proper import: e.g. the module
        is not put into sys.modules
        """
        so_filename = self.compile_module(ExtensionTemplate, main_src, name,
                                          extra_sources)
        if self.hpy_abi == 'universal':
            return self.load_universal_module(name, so_filename)
        else:
            return self.load_cython_module(name, so_filename)

    def load_universal_module(self, name, so_filename):
        assert self.hpy_abi == 'universal'
        import hpy.universal
        spec = Spec(name, so_filename)
        return hpy.universal.load_from_spec(spec)

    def load_cython_module(self, name, so_filename):
        assert self.hpy_abi == 'cpython'
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
    ExtensionTemplate = DefaultExtensionTemplate

    @pytest.fixture()
    def initargs(self, compiler):
        # compiler is a fixture defined in conftest
        self.compiler = compiler

    def make_module(self, main_src, name='mytest', extra_sources=()):
        ExtensionTemplate = self.ExtensionTemplate
        return self.compiler.make_module(ExtensionTemplate, main_src, name,
                                         extra_sources)

    def should_check_refcount(self):
        # defaults to True on CPython, but is set to False by e.g. PyPy
        return sys.implementation.name == 'cpython'


# the few functions below are copied and adapted from cffi/ffiplatform.py

def c_compile(tmpdir, ext, hpy_devel, hpy_abi, compiler_verbose=0, debug=None):
    """Compile a C extension module using distutils."""
    saved_environ = os.environ.copy()
    try:
        outputfilename = _build(tmpdir, ext, hpy_devel, hpy_abi, compiler_verbose, debug)
        outputfilename = os.path.abspath(outputfilename)
    finally:
        # workaround for a distutils bugs where some env vars can
        # become longer and longer every time it is used
        for key, value in saved_environ.items():
            if os.environ.get(key) != value:
                os.environ[key] = value
    return outputfilename

def _build(tmpdir, ext, hpy_devel, hpy_abi, compiler_verbose=0, debug=None):
    # XXX compact but horrible :-(
    from distutils.core import Distribution
    import distutils.errors, distutils.log
    #
    dist = Distribution()
    dist.parse_config_files()
    options = dist.get_option_dict('build_ext')
    if debug is None:
        debug = sys.flags.debug
    options['debug'] = ('ffiplatform', debug)
    options['force'] = ('ffiplatform', True)
    options['build_lib'] = ('ffiplatform', tmpdir)
    options['build_temp'] = ('ffiplatform', tmpdir)
    #
    # this is the equivalent of passing --hpy-abi from setup.py's command line
    dist.hpy_abi = hpy_abi
    hpy_devel.fix_distribution(dist, hpy_ext_modules=[ext])
    #
    old_level = distutils.log.set_threshold(0) or 0
    try:
        distutils.log.set_verbosity(compiler_verbose)
        dist.run_command('build_ext')
        cmd_obj = dist.get_command_obj('build_ext')
        [soname] = cmd_obj.get_outputs()
    finally:
        distutils.log.set_threshold(old_level)
    #
    return soname
