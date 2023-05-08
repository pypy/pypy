import os, sys
from filelock import FileLock
import pytest
from pathlib import Path
import re
import subprocess
import textwrap
import distutils

PY2 = sys.version_info[0] == 2

HPY_ROOT = Path(__file__).parent.parent
LOCK = FileLock(HPY_ROOT / ".hpy.lock")

# True if `sys.executable` is set to a value that allows a Python equivalent to
# the current Python to be launched via, e.g., `python_subprocess.run(...)`.
# By default is `True` if sys.executable is set to a true value.
SUPPORTS_SYS_EXECUTABLE = bool(getattr(sys, "executable", None))
# True if we are running on the CPython debug build
IS_PYTHON_DEBUG_BUILD = hasattr(sys, 'gettotalrefcount')

# pytest marker to run tests only on linux
ONLY_LINUX = pytest.mark.skipif(sys.platform!='linux', reason='linux only')

SUPPORTS_MEM_PROTECTION = '_HPY_DEBUG_FORCE_DEFAULT_MEM_PROTECT' not in os.environ

def reindent(s, indent):
    s = textwrap.dedent(s)
    return ''.join(' '*indent + line if line.strip() else line
        for line in s.splitlines(True))

def atomic_run(*args, **kwargs):
    with LOCK:
        return subprocess.run(*args, **kwargs)


def make_hpy_abi_fixture(ABIs, class_fixture=False):
    """
    Make an hpy_abi fixture.

    conftest.py defines a default hpy_abi for all tests, but individual files
    and classes can override the set of ABIs they want to use. The indented
    usage is the following:

    # at the top of a file
    hpy_abi = make_hpy_abi_fixture(['universal', 'debug'])

    # in a class
    class TestFoo(HPyTest):
        hpy_abi = make_hpy_abi_fixture('with hybrid', class_fixture=True)
    """
    if ABIs == 'default':
        ABIs = ['cpython', 'universal', 'debug']
    elif ABIs == 'with hybrid':
        ABIs = ['cpython', 'hybrid', 'hybrid+debug']
    elif isinstance(ABIs, list):
        pass
    else:
        raise ValueError("ABIs must be 'default', 'with hybrid' "
                         "or a list of strings. Got: %s" % ABIs)

    if class_fixture:
        @pytest.fixture(params=ABIs)
        def hpy_abi(self, request):
            abi = request.param
            yield abi
    else:
        @pytest.fixture(params=ABIs)
        def hpy_abi(request):
            abi = request.param
            yield abi

    return hpy_abi


class DefaultExtensionTemplate(object):

    INIT_TEMPLATE = textwrap.dedent(
    """
    static HPyDef *moduledefs[] = {
        %(defines)s
        NULL
    };
    %(globals_defs)s
    static HPyModuleDef moduledef = {
        .doc = "some test for hpy",
        .size = 0,
        .legacy_methods = %(legacy_methods)s,
        .defines = moduledefs,
        %(globals_field)s
    };

    HPy_MODINIT(%(name)s, moduledef)
    """)

    INIT_TEMPLATE_WITH_TYPES_INIT = textwrap.dedent(
        """
        HPyDef_SLOT(generated_init, HPy_mod_exec)
        static int generated_init_impl(HPyContext *ctx, HPy m)
        {
            // Shouldn't really happen, but jut to silence the unused label warning
            if (HPy_IsNull(m))
                goto MODINIT_ERROR;

            %(init_types)s
            return 0;

            MODINIT_ERROR:
            return -1;
        }
        """ + INIT_TEMPLATE)

    r_marker = re.compile(r"^\s*@([A-Za-z_]+)(\(.*\))?$")

    def __init__(self, src, name):
        self.src = textwrap.dedent(src)
        self.name = name
        self.defines_table = None
        self.legacy_methods = 'NULL'
        self.type_table = None
        self.globals_table = None

    def expand(self):
        self.defines_table = []
        self.globals_table = []
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
        NL_INDENT = '\n    '
        if self.type_table:
            init_types = '\n'.join(self.type_table)
        else:
            init_types = ''

        globals_defs = ''
        globals_field = ''
        if self.globals_table:
            globals_defs = \
                textwrap.dedent('''
                static HPyGlobal *module_globals[] = {
                    %s
                    NULL
                };''') % NL_INDENT.join(self.globals_table)
            globals_field = '.globals = module_globals'

        template = self.INIT_TEMPLATE
        if init_types:
            template = self.INIT_TEMPLATE_WITH_TYPES_INIT
            self.EXPORT('generated_init')
        exp = template % {
            'legacy_methods': self.legacy_methods,
            'defines': NL_INDENT.join(self.defines_table),
            'init_types': init_types,
            'name': self.name,
            'globals_defs': globals_defs,
            'globals_field': globals_field}
        self.output.append(exp)
        # make sure that we don't fill the tables any more
        self.defines_table = None
        self.type_table = None

    def EXPORT(self, meth):
        self.defines_table.append('&%s,' % meth)

    def EXPORT_GLOBAL(self, var):
        self.globals_table.append('&%s,' % var)

    def EXPORT_LEGACY(self, pymethoddef):
        self.legacy_methods = pymethoddef

    def EXPORT_TYPE(self, name, spec):
        src = """
            if (!HPyHelpers_AddType(ctx, m, {name}, &{spec}, NULL)) {{
                goto MODINIT_ERROR;
            }}
            """
        src = reindent(src, 4)
        self.type_table.append(src.format(
            name=name,
            spec=spec))

    def EXTRA_INIT_FUNC(self, func):
        src = """
            {func}(ctx, m);
            if (HPyErr_Occurred(ctx))
                goto MODINIT_ERROR;
            """
        src = reindent(src, 4)
        self.type_table.append(src.format(func=func))

    def HPy_MODINIT(self, mod):
        return "HPy_MODINIT({}, {})".format(self.name, mod)


class Spec(object):
    def __init__(self, name, origin):
        self.name = name
        self.origin = origin


class HPyModule(object):
    def __init__(self, name, so_file):
        self.name = name
        self.so_filename = so_file


class ExtensionCompiler:
    def __init__(self, tmpdir, hpy_devel, hpy_abi, compiler_verbose=False,
                 dump_dir=None,
                 ExtensionTemplate=DefaultExtensionTemplate,
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
        self.dump_dir = dump_dir
        self.hpy_devel = hpy_devel
        self.hpy_abi = hpy_abi
        self.compiler_verbose = compiler_verbose
        self.ExtensionTemplate = ExtensionTemplate
        self.extra_include_dirs = extra_include_dirs

    def _expand(self, ExtensionTemplate, name, template):
        source = ExtensionTemplate(template, name).expand()
        filename = self.tmpdir.join(name + '.c')
        dump_file = self.dump_dir.joinpath(name + '.c') if self.dump_dir else None
        if PY2:
            # this code is used also by pypy tests, which run on python2. In
            # this case, we need to write as binary, because source is
            # "bytes". If we don't and source contains a non-ascii char, we
            # get an UnicodeDecodeError
            if dump_file:
                dump_file.write_text(source)
            filename.write(source, mode='wb')
        else:
            if dump_file:
                dump_file.write_text(source)
            filename.write(source)
        return name + '.c'

    def _fixup_template(self, ExtensionTemplate):
        return self.ExtensionTemplate if ExtensionTemplate is None else ExtensionTemplate

    def compile_module(self, main_src, ExtensionTemplate=None, name='mytest', extra_sources=()):
        """
        Create and compile a HPy module from the template
        """
        ExtensionTemplate = self._fixup_template(ExtensionTemplate)
        from distutils.core import Extension
        filename = self._expand(ExtensionTemplate, name, main_src)
        sources = [str(filename)]
        for i, src in enumerate(extra_sources):
            extra_filename = self._expand(ExtensionTemplate, 'extmod_%d' % i, src)
            sources.append(extra_filename)
        #
        if self.dump_dir:
            pytest.skip("dumping test sources only")
        if sys.platform == 'win32':
            # not strictly true, could be mingw
            compile_args = [
                '/Od',
                '/WX',               # turn warnings into errors (all, for now)
                # '/Wall',           # this is too aggressive, makes windows itself fail
                '/Zi',
                '-D_CRT_SECURE_NO_WARNINGS', # something about _snprintf and _snprintf_s
                '/FS',               # Since the tests run in parallel
            ]
            link_args = [
                '/DEBUG',
                '/LTCG',
            ]
        else:
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

        hpy_abi = self.hpy_abi
        if hpy_abi == 'debug' or hpy_abi == 'trace':
            # there is no compile-time difference between universal and debug
            # extensions. The only difference happens at load time
            hpy_abi = 'universal'
        elif hpy_abi in ('hybrid+debug', 'hybrid+trace'):
            hpy_abi = 'hybrid'
        so_filename = c_compile(str(self.tmpdir), ext,
                                hpy_devel=self.hpy_devel,
                                hpy_abi=hpy_abi,
                                compiler_verbose=self.compiler_verbose)
        return HPyModule(name, so_filename)

    def make_module(self, main_src, ExtensionTemplate=None, name='mytest',
                    extra_sources=()):
        """
        Compile & load a module. This is NOT a proper import: e.g.
        the module is not put into sys.modules.

        We don't want to unnecessarily modify the global state inside tests:
        if you are writing a test which needs a proper import, you should not
        use make_module but explicitly use compile_module and import it
        manually as required by your test.
        """
        ExtensionTemplate = self._fixup_template(ExtensionTemplate)
        module = self.compile_module(
            main_src, ExtensionTemplate, name, extra_sources)
        so_filename = module.so_filename
        from hpy.universal import MODE_UNIVERSAL, MODE_DEBUG, MODE_TRACE
        if self.hpy_abi in ('universal', 'hybrid'):
            return self.load_universal_module(name, so_filename, mode=MODE_UNIVERSAL)
        elif self.hpy_abi in ('debug', 'hybrid+debug'):
            return self.load_universal_module(name, so_filename, mode=MODE_DEBUG)
        elif self.hpy_abi in ('trace', 'hybrid+trace'):
            return self.load_universal_module(name, so_filename, mode=MODE_TRACE)
        elif self.hpy_abi == 'cpython':
            return self.load_cpython_module(name, so_filename)
        else:
            assert False

    def load_universal_module(self, name, so_filename, mode):
        assert self.hpy_abi in ('universal', 'hybrid', 'debug', 'hybrid+debug',
                                'trace', 'hybrid+trace')
        import sys
        import hpy.universal
        import importlib.util
        assert name not in sys.modules
        spec = importlib.util.spec_from_file_location(name, so_filename)
        mod = hpy.universal.load(name, so_filename, spec, mode=mode)
        mod.__file__ = so_filename
        mod.__spec__ = spec
        return mod

    def load_cpython_module(self, name, so_filename):
        assert self.hpy_abi == 'cpython'
        # we've got a normal CPython module compiled with the CPython API/ABI,
        # let's load it normally. It is important to do the imports only here,
        # because this file will be imported also by PyPy tests which runs on
        # Python2
        import importlib.util
        import sys
        assert name not in sys.modules
        spec = importlib.util.spec_from_file_location(name, so_filename)
        try:
            # module_from_spec adds the module to sys.modules
            module = importlib.util.module_from_spec(spec)
        finally:
            if name in sys.modules:
                del sys.modules[name]
        spec.loader.exec_module(module)
        return module


class PythonSubprocessRunner:
    def __init__(self, verbose, hpy_abi):
        self.verbose = verbose
        self.hpy_abi = hpy_abi

    def run(self, mod, code):
        """ Starts new subprocess that loads given module as 'mod' using the
            correct ABI mode and then executes given code snippet. Use
            "--subprocess-v" to enable logging from this.
        """
        env = os.environ.copy()
        pythonpath = [os.path.dirname(mod.so_filename)]
        if 'PYTHONPATH' in env:
            pythonpath.append(env['PYTHONPATH'])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath)
        if self.hpy_abi in ['universal', 'debug']:
            # HPy module
            load_module = "import sys;" + \
                          "import hpy.universal;" + \
                          "import importlib.util;" + \
                          "spec = importlib.util.spec_from_file_location('{name}', '{so_filename}');" + \
                          "mod = hpy.universal.load('{name}', '{so_filename}', spec, debug={debug});"
            escaped_filename = mod.so_filename.replace("\\", "\\\\")  # Needed for Windows paths
            load_module = load_module.format(name=mod.name, so_filename=escaped_filename,
                                             debug=self.hpy_abi == 'debug')
        else:
            # CPython module
            assert self.hpy_abi == 'cpython'
            load_module = "import {} as mod;".format(mod.name)
        if self.verbose:
            print("\n---\nExecuting in subprocess: {}".format(load_module + code))
        result = atomic_run([sys.executable, "-c", load_module + code], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if self.verbose:
            print("stdout/stderr:")
            try:
                out = result.stdout.decode('latin-1')
                err = result.stderr.decode('latin-1')
                print("----\n{out}--\n{err}-----".format(out=out, err=err))
            except UnicodeDecodeError:
                print("Warning: stdout or stderr could not be decoded with 'latin-1' encoding")
        return result


@pytest.mark.usefixtures('initargs')
class HPyTest:
    ExtensionTemplate = DefaultExtensionTemplate

    @pytest.fixture()
    def initargs(self, compiler, leakdetector, capfd):
        self.compiler = compiler
        self.leakdetector = leakdetector
        self.capfd = capfd

    def make_module(self, main_src, name='mytest', extra_sources=()):
        ExtensionTemplate = self.ExtensionTemplate
        return self.compiler.make_module(main_src, ExtensionTemplate, name,
                                         extra_sources)

    def compile_module(self, main_src, name='mytest', extra_sources=()):
        ExtensionTemplate = self.ExtensionTemplate
        return self.compiler.compile_module(main_src, ExtensionTemplate, name,
                                     extra_sources)

    def expect_make_error(self, main_src, error):
        with pytest.raises(distutils.errors.CompileError):
            self.make_module(main_src)
        #
        # capfd.readouterr() "eats" the output, but we want to still see it in
        # case of failure. Just print it again
        cap = self.capfd.readouterr()
        sys.stdout.write(cap.out)
        sys.stderr.write(cap.err)
        #
        # gcc prints compiler errors to stderr, but MSVC seems to print them
        # to stdout. Let's just check both
        if error in cap.out or error in cap.err:
            # the error was found, we are good
            return
        raise Exception("The following error message was not found in the compiler "
                        "output:\n    " + error)


    def supports_refcounts(self):
        """ Returns True if the underlying Python implementation supports
            reference counts.

            By default, returns True on CPython and False on other
            implementations.
        """
        return sys.implementation.name == "cpython"

    def supports_ordinary_make_module_imports(self):
        """ Returns True if `.make_module(...)` loads modules using a
            standard Python import mechanism (e.g. `importlib.import_module`).

            By default, returns True because the base implementation of
            `.make_module(...)` uses an ordinary import. Sub-classes that
            override `.make_module(...)` may also want to override this
            method.
        """
        return True

    def supports_refcounts(self):
        """ Returns True if the underlying Python implementation supports
            the vectorcall protocol.

            By default, this returns True for Python version 3.8+ on all
            implementations.
        """
        return sys.version_info >= (3, 8)


class HPyDebugCapture:
    """
    Context manager that sets HPy debug invalid handle hook and remembers the
    number of invalid handles reported. Once closed, sets the invalid handle
    hook back to None.
    """
    def __init__(self):
        self.invalid_handles_count = 0
        self.invalid_builders_count = 0

    def _capture_report(self):
        self.invalid_handles_count += 1

    def _capture_builder_report(self):
        self.invalid_builders_count += 1

    def __enter__(self):
        from hpy.universal import _debug
        _debug.set_on_invalid_handle(self._capture_report)
        _debug.set_on_invalid_builder_handle(self._capture_builder_report)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        from hpy.universal import _debug
        _debug.set_on_invalid_handle(None)
        _debug.set_on_invalid_builder_handle(None)


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
    import distutils.errors
    import distutils.log
    #
    dist = Distribution()
    dist.parse_config_files()
    if debug is None:
        debug = sys.flags.debug
    options_build_ext = dist.get_option_dict('build_ext')
    options_build_ext['debug'] = ('ffiplatform', debug)
    options_build_ext['force'] = ('ffiplatform', True)
    options_build_ext['build_lib'] = ('ffiplatform', tmpdir)
    options_build_ext['build_temp'] = ('ffiplatform', tmpdir)
    options_build_py = dist.get_option_dict('build_py')
    options_build_py['build_lib'] = ('ffiplatform', tmpdir)

    # this is the equivalent of passing --hpy-abi from setup.py's command line
    dist.hpy_abi = hpy_abi
    # For testing, we want to use static libs to avoid repeated compilation
    # of the same sources which slows down testing.
    dist.hpy_use_static_libs = True
    dist.hpy_ext_modules = [ext]
    # We need to explicitly specify which Python modules we expect because some
    # test cases create several distributions in the same temp directory.
    dist.py_modules = [ext.name]
    hpy_devel.fix_distribution(dist)

    old_level = distutils.log.set_threshold(0) or 0
    old_dir = os.getcwd()
    try:
        os.chdir(tmpdir)
        distutils.log.set_verbosity(compiler_verbose)
        dist.run_command('build_ext')
        cmd_obj = dist.get_command_obj('build_ext')
        outputs = cmd_obj.get_outputs()
        sonames = [x for x in outputs if
                   not x.endswith(".py") and not x.endswith(".pyc")]
        assert len(sonames) == 1, 'build_ext is not supposed to return multiple DLLs'
        soname = sonames[0]
    finally:
        os.chdir(old_dir)
        distutils.log.set_threshold(old_level)

    return soname


# For situations when one wants to have "support.py" on the call stack.
# For example, for asserting that it is in a stack trace.
def trampoline(fun, *args, **kwargs):
    fun(*args, **kwargs)
