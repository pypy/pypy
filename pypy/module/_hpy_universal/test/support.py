import py
import pytest
import sys
from rpython.tool.udir import udir
from pypy.interpreter.gateway import interp2app, unwrap_spec, W_Root
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module._hpy_universal.llapi import BASE_DIR
from pypy.module._hpy_universal.test._vendored import support as _support
from pypy.module._hpy_universal._vendored.hpy.devel import HPyDevel
from ..state import State
from .. import llapi

COMPILER_VERBOSE = False

# Module-level cache: built once, reused for every test that calls _init.
# Maps hpy_abi string -> {abi: [lib_path]} dict (empty dict means build failed).
_static_lib_cache = {}

# Cache compiled .so files by (source, template, name, extra_sources, hpy_abi).
# universal/debug share the same compiled artifact; hybrid/hybrid+debug share
# another. This is safe because hpy_abi is already normalized before the
# ExtensionCompiler is created.
_compiled_module_cache = {}  # (main_src, template_name, name, extra_sources, hpy_abi) -> so_filename

def _try_build_static_lib(hpy_devel, hpy_abi):
    """
    Compile the HPy helper sources into a static archive once per session.
    Returns {hpy_abi: [lib_path]} on success, {} on failure.
    """
    try:
        import distutils.ccompiler
        import distutils.sysconfig
        import os

        base = udir.join('hpy_staticlib')
        abi_dir = base.join(hpy_abi)
        abi_dir.ensure(dir=True)
        obj_dir = base.join('obj', hpy_abi)
        obj_dir.ensure(dir=True)

        compiler = distutils.ccompiler.new_compiler()
        distutils.sysconfig.customize_compiler(compiler)

        include_dirs = hpy_devel.get_extra_include_dirs()
        include_dirs.append(str(hpy_devel.get_include_dir_forbid_python_h()))
        macros = [('HPY', None), ('HPY_ABI_UNIVERSAL', None)]

        objects = compiler.compile(
            hpy_devel.get_extra_sources(),
            output_dir=str(obj_dir),
            include_dirs=include_dirs,
            macros=macros,
        )

        lib_name = 'hpyextra'
        compiler.create_static_lib(objects, lib_name, output_dir=str(abi_dir))
        lib_filename = compiler.library_filename(lib_name, lib_type='static')
        lib_path = str(abi_dir.join(lib_filename))
        return {'universal': [lib_path], 'hybrid': [lib_path]}
    except Exception as e:
        import warnings
        warnings.warn(
            "HPy static-lib build failed (%s); "
            "falling back to per-test source compilation." % e,
            stacklevel=2,
        )
        return {}


def debug_collect():
    import gc
    gc.collect()

class HPyAppTest(object):
    """
    Base class for HPy app tests. This is used as a mixin, and individual
    subclasses are created by conftest.make_hpy_apptest
    """

    extra_link_args = []
    spaceconfig = {
        'usemodules': ['_hpy_universal'],
        'objspace.hpy_cpyext_API': False,
    }

    def setup_class(cls):
        if cls.runappdirect:
            pytest.skip()
        cls.w_runappdirect = cls.space.wrap(cls.runappdirect)
        cls.w_debug_collect = cls.space.wrap(interp2app(debug_collect))

    @pytest.fixture
    def compiler(self):
        # see setup_method below
        return 'The fixture "compiler" is not used on pypy'

    # NOTE: HPyTest has already an initargs fixture, but it's ignored here
    # because pypy is using an old pytest version which does not support
    # @pytest.mark.usefixtures on classes. To work around the limitation, we
    # redeclare initargs as autouse=True, so it's automatically used by all
    # tests.
    @pytest.fixture(params=['universal', 'debug'], autouse=True)
    def initargs(self, request, capfd):
        hpy_abi = request.param
        self._init(request, hpy_abi)
        self.capfd = capfd

    def _init(self, request, hpy_abi):
        state = self.space.fromcache(State)
        if state.was_already_setup():
            state.reset()
        if self.space.config.objspace.usemodules.cpyext:
            from pypy.module import cpyext
            cpyext_include_dirs = cpyext.api.include_dirs
        else:
            cpyext_include_dirs = None
        self.w_hpy_abi = self.space.newtext(hpy_abi)
        #
        # it would be nice to use the 'compiler' fixture to provide
        # make_module as the std HPyTest do. However, we don't have the space
        # yet, so it is much easier to prove make_module() here
        prefix = request.function.__name__ + '-'
        if sys.platform == 'win32':
            prefix = prefix.lower()
        tmpdir = py.path.local.make_numbered_dir(rootdir=udir,
                                                 prefix=prefix,
                                                 keep=0)  # keep everything

        hpy_devel = HPyDevel(str(BASE_DIR))
        if 'libs' not in _static_lib_cache:
            _static_lib_cache['libs'] = _try_build_static_lib(hpy_devel, 'universal')
        if _static_lib_cache['libs']:
            hpy_devel._available_static_libs = _static_lib_cache['libs']
        if hpy_abi in ("debug", "hybrid+debug"):
            mode = llapi.MODE_DEBUG
        elif hpy_abi in ("universal", "hybrid"):
            mode = llapi.MODE_UNIVERSAL
        elif hpy_abi == "trace":
            mode = llapi.MODE_TRACE
        else:
            mode = -1
        if hpy_abi == 'debug' or hpy_abi == 'trace':
            # there is no compile-time difference between universal and debug
            # extensions. The only difference happens at load time
            hpy_abi = 'universal'
        elif hpy_abi in ('hybrid+debug', 'hybrid+trace'):
            hpy_abi = 'hybrid'
        compiler = _support.ExtensionCompiler(tmpdir, hpy_devel, hpy_abi,
                                              compiler_verbose=COMPILER_VERBOSE,
                                              extra_link_args=self.extra_link_args,
                                              extra_include_dirs=cpyext_include_dirs)
        ExtensionTemplate = self.ExtensionTemplate

        @unwrap_spec(main_src='text', name='text', w_extra_sources=W_Root)
        def descr_make_module(space, main_src, name='mytest',
                              w_extra_sources=None):
            if w_extra_sources is None:
                extra_sources = ()
            else:
                items_w = space.unpackiterable(w_extra_sources)
                extra_sources = [space.text_w(item) for item in items_w]
            # Include mode in the cache key so that different ABI modes
            # (e.g. universal vs debug) get separate .so files.  Both
            # compile identically but are loaded as distinct shared
            # libraries, which prevents C-level static variables from
            # leaking between runs (e.g. test_tp_finalize's
            # saw_expected_finalize_call / test_finished).
            cache_key = (main_src, ExtensionTemplate.__name__,
                         name, tuple(extra_sources), hpy_abi, mode)
            if cache_key in _compiled_module_cache:
                so_filename = _compiled_module_cache[cache_key]
            else:
                module = compiler.compile_module(main_src, ExtensionTemplate,
                                                 name, extra_sources)
                so_filename = module.so_filename
                _compiled_module_cache[cache_key] = so_filename
            w_mod = space.appexec([space.newtext(name),
                                   space.newtext(so_filename),
                                   space.newint(mode)],
                """(name, so_filename, mode):
                    import sys
                    import _hpy_universal
                    import importlib.util
                    assert name not in sys.modules
                    spec = importlib.util.spec_from_file_location(name, so_filename)
                    mod = _hpy_universal.load(name, so_filename, spec, mode=mode)
                    mod.__file__ = so_filename
                    mod.__spec__ = spec
                    return mod
                """
            )
            return w_mod
        self.w_make_module = self.space.wrap(interp2app(descr_make_module))

        @unwrap_spec(main_src='text', w_ExtensionTemplate=W_Root, name='text',
                     w_extra_sources=W_Root)
        def descr_compile_module(space, main_src, w_ExtensionTemplate=None,
                           name='mytest', w_extra_sources=None):
            if w_extra_sources is None:
                extra_sources = ()
            else:
                items_w = space.unpackiterable(w_extra_sources)
                extra_sources = [space.text_w(item) for item in items_w]
            if w_ExtensionTemplate is not None:
                raise NotImplementedError
            cache_key = (main_src, ExtensionTemplate.__name__,
                         name, tuple(extra_sources), hpy_abi, mode)
            if cache_key in _compiled_module_cache:
                so_filename = _compiled_module_cache[cache_key]
            else:
                module = compiler.compile_module(main_src, ExtensionTemplate,
                                                 name, extra_sources)
                so_filename = module.so_filename
                _compiled_module_cache[cache_key] = so_filename
            # All we need for tests is module.so_filename
            w_class_with_so_filename = space.appexec([
                    space.newtext(so_filename)],
                """(so_filename,):
                    class ClassWithSoFilename():
                        def __init__(self, so_filename):
                            self.so_filename = so_filename
                    return ClassWithSoFilename(so_filename)
                """
            )
            return w_class_with_so_filename
        self.w_compile_module = self.space.wrap(interp2app(descr_compile_module))

        def supports_refcounts(space):
            return space.w_False
        self.w_supports_refcounts = self.space.wrap(interp2app(supports_refcounts))

        def supports_ordinary_make_module_imports(space):
            return space.w_False
        self.w_supports_ordinary_make_module_imports = self.space.wrap(
            interp2app(supports_ordinary_make_module_imports))

        def supports_sys_executable(space):
            return space.w_False
        self.w_supports_sys_executable = self.space.wrap(
            interp2app(supports_sys_executable))

        @unwrap_spec(name='text', so_filename='text', mode=int)
        def descr_load_universal_module(space, name, so_filename, mode):
            w_mod = space.appexec([space.newtext(name),
                                   space.newtext(so_filename),
                                   space.newint(mode)],
                """(modname, so_filename, mode):
                    import _hpy_universal
                    return _hpy_universal.load(modname, so_filename, mode)
                """
            )
            return w_mod

        w_load_universal_module = self.space.wrap(interp2app(descr_load_universal_module))

        self.w_compiler = self.space.appexec([self.space.newtext(hpy_abi),
                                              w_load_universal_module,
                                             ],
            """(abi, _load_universal_module):
                class compiler:
                    hpy_abi = abi
                    load_universal_module = _load_universal_module
                return compiler
            """)

        @unwrap_spec(main_src='text', error='text')
        def descr_expect_make_error(space, main_src, error):
            try:
                compiler.compile_module(main_src, ExtensionTemplate, "mytest")
            except Exception as err:
                pass
            #
            # capfd.readouterr() "eats" the output, but we want to still see it in
            # case of failure. Just print it again
            cap = self.capfd.readouterr()
            sys.stdout.write(cap[0])
            sys.stderr.write(cap[1])
            #
            # gcc prints compiler errors to stderr, but MSVC seems to print them
            # to stdout. Let's just check both
            if error in cap[0] or error in cap[1]:
                # the error was found, we are good
                return
            raise Exception("The following error message was not found in the compiler "
                        "output:\n    " + error)

        self.w_expect_make_error = self.space.wrap(interp2app(descr_expect_make_error))

class HPyDebugAppTest(HPyAppTest):

    # override the initargs fixture to run the tests ONLY in debug mode, as
    # done by upstream's HPyDebugTest
    @pytest.fixture(autouse=True)
    def initargs(self, request):
        self._init(request, hpy_abi='debug')

    # make self.make_leak_module() available to the tests. Note that this is
    # code which will be run at applevel, and will call self.make_module,
    # which is finally executed at interp-level (see descr_make_module above)
    #w_make_leak_module = _support.HPyDebugTest.make_leak_module


if sys.platform == 'win32':
    # since we include Python.h, we must disable linking with the regular
    # import lib
    from pypy.module.sys import version
    ver = version.CPYTHON_VERSION[:2]
    untranslated_link_args = ["/NODEFAULTLIB:Python%d%d.lib" % ver]
    untranslated_link_args.append(str(udir / "module_cache" / "pypyapi.lib"))
else:
    untranslated_link_args = []

class HPyCPyextAppTest(AppTestCpythonExtensionBase, HPyAppTest):
    """
    Base class for hpy tests which also need cpyext
    """

    extra_link_args = untranslated_link_args

    # mmap is needed because it is imported by LeakCheckingTest.setup_class
    spaceconfig = {'usemodules': ['_hpy_universal', 'cpyext', 'mmap']}

    def setup_class(cls):
        HPyAppTest.setup_class.im_func(cls)
        AppTestCpythonExtensionBase.setup_class.im_func(cls)

    # override the initargs fixture to run the tests in hybrid mode
    @pytest.fixture(params=['hybrid', 'hybrid+debug'], autouse=True)
    def initargs(self, request):
        hpy_abi = request.param
        self._init(request, hpy_abi)


