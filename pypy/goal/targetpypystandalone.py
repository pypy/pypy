import py

import os, sys, subprocess

import pypy
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.tool.ann_override import PyPyAnnotatorPolicy
from rpython.config.config import to_optparse, make_dict, SUPPRESS_USAGE
from rpython.config.config import ConflictConfigError
from pypy.tool.option import make_objspace
from pypy import pypydir
from rpython.rlib import rthread
from pypy.module.thread import os_thread

thisdir = py.path.local(__file__).dirpath()

try:
    this_dir = os.path.dirname(__file__)
except NameError:
    this_dir = os.path.dirname(sys.argv[0])

def debug(msg):
    try:
        os.write(2, "debug: " + msg + '\n')
    except OSError:
        pass     # bah, no working stderr :-(

# __________  Entry point  __________


def create_entry_point(space, w_dict):
    if w_dict is not None: # for tests
        w_entry_point = space.getitem(w_dict, space.wrap('entry_point'))
        w_run_toplevel = space.getitem(w_dict, space.wrap('run_toplevel'))
        withjit = space.config.objspace.usemodules.pypyjit

    def entry_point(argv):
        if withjit:
            from rpython.jit.backend.hlinfo import highleveljitinfo
            highleveljitinfo.sys_executable = argv[0]

        #debug("entry point starting")
        #for arg in argv:
        #    debug(" argv -> " + arg)
        if len(argv) > 2 and argv[1] == '--heapsize':
            # Undocumented option, handled at interp-level.
            # It has silently no effect with some GCs.
            # It works in Boehm and in the semispace or generational GCs
            # (but see comments in semispace.py:set_max_heap_size()).
            # At the moment this option exists mainly to support sandboxing.
            from rpython.rlib import rgc
            rgc.set_max_heap_size(int(argv[2]))
            argv = argv[:1] + argv[3:]
        try:
            try:
                space.startup()
                w_executable = space.wrap(argv[0])
                w_argv = space.newlist([space.wrap(s) for s in argv[1:]])
                w_exitcode = space.call_function(w_entry_point, w_executable, w_argv)
                exitcode = space.int_w(w_exitcode)
                # try to pull it all in
            ##    from pypy.interpreter import main, interactive, error
            ##    con = interactive.PyPyConsole(space)
            ##    con.interact()
            except OperationError as e:
                debug("OperationError:")
                debug(" operror-type: " + e.w_type.getname(space))
                debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
                return 1
        finally:
            try:
                space.finish()
            except OperationError as e:
                debug("OperationError:")
                debug(" operror-type: " + e.w_type.getname(space))
                debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
                return 1
        return exitcode

    # register the minimal equivalent of running a small piece of code. This
    # should be used as sparsely as possible, just to register callbacks

    from rpython.rlib.entrypoint import entrypoint_highlevel
    from rpython.rtyper.lltypesystem import rffi, lltype

    @entrypoint_highlevel('main', [rffi.CCHARP, rffi.INT],
                          c_name='pypy_setup_home')
    def pypy_setup_home(ll_home, verbose):
        from pypy.module.sys.initpath import pypy_find_stdlib
        verbose = rffi.cast(lltype.Signed, verbose)
        if ll_home and ord(ll_home[0]):
            home1 = rffi.charp2str(ll_home)
            home = os.path.join(home1, 'x') # <- so that 'll_home' can be
                                            # directly the root directory
        else:
            home1 = "pypy's shared library location"
            home = '*'
        w_path = pypy_find_stdlib(space, home)
        if space.is_none(w_path):
            if verbose:
                debug("pypy_setup_home: directories 'lib-python' and 'lib_pypy'"
                      " not found in %s or in any parent directory" % home1)
            return rffi.cast(rffi.INT, 1)
        space.startup()
        space.appexec([w_path], """(path):
            import sys
            sys.path[:] = path
        """)
        # import site
        try:
            space.setattr(space.getbuiltinmodule('sys'),
                          space.wrap('executable'),
                          space.wrap(home))
            import_ = space.getattr(space.getbuiltinmodule('__builtin__'),
                                    space.wrap('__import__'))
            space.call_function(import_, space.wrap('site'))
            return rffi.cast(rffi.INT, 0)
        except OperationError as e:
            if verbose:
                debug("OperationError:")
                debug(" operror-type: " + e.w_type.getname(space))
                debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
            return rffi.cast(rffi.INT, -1)

    @entrypoint_highlevel('main', [rffi.CCHARP], c_name='pypy_execute_source')
    def pypy_execute_source(ll_source):
        return pypy_execute_source_ptr(ll_source, 0)

    @entrypoint_highlevel('main', [rffi.CCHARP, lltype.Signed],
                          c_name='pypy_execute_source_ptr')
    def pypy_execute_source_ptr(ll_source, ll_ptr):
        source = rffi.charp2str(ll_source)
        res = _pypy_execute_source(source, ll_ptr)
        return rffi.cast(rffi.INT, res)

    @entrypoint_highlevel('main', [], c_name='pypy_init_threads')
    def pypy_init_threads():
        if not space.config.objspace.usemodules.thread:
            return
        os_thread.setup_threads(space)

    @entrypoint_highlevel('main', [], c_name='pypy_thread_attach')
    def pypy_thread_attach():
        if not space.config.objspace.usemodules.thread:
            return
        os_thread.setup_threads(space)
        os_thread.bootstrapper.acquire(space, None, None)
        # XXX this doesn't really work.  Don't use os.fork(), and
        # if your embedder program uses fork(), don't use any PyPy
        # code in the fork
        rthread.gc_thread_start()
        os_thread.bootstrapper.nbthreads += 1
        os_thread.bootstrapper.release()

    def _pypy_execute_source(source, c_argument):
        try:
            w_globals = space.newdict(module=True)
            space.setitem(w_globals, space.wrap('__builtins__'),
                          space.builtin_modules['__builtin__'])
            space.setitem(w_globals, space.wrap('c_argument'),
                          space.wrap(c_argument))
            space.appexec([space.wrap(source), w_globals], """(src, glob):
                import sys
                stmt = compile(src, 'c callback', 'exec')
                if not hasattr(sys, '_pypy_execute_source'):
                    sys._pypy_execute_source = []
                sys._pypy_execute_source.append(glob)
                exec stmt in glob
            """)
        except OperationError as e:
            debug("OperationError:")
            debug(" operror-type: " + e.w_type.getname(space))
            debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
            return -1
        return 0

    return entry_point, {'pypy_execute_source': pypy_execute_source,
                         'pypy_execute_source_ptr': pypy_execute_source_ptr,
                         'pypy_init_threads': pypy_init_threads,
                         'pypy_thread_attach': pypy_thread_attach,
                         'pypy_setup_home': pypy_setup_home}


# _____ Define and setup target ___

# for now this will do for option handling

class PyPyTarget(object):

    usage = SUPPRESS_USAGE

    take_options = True

    def opt_parser(self, config):
        parser = to_optparse(config, useoptions=["objspace.*"],
                             parserkwargs={'usage': self.usage})
        return parser

    def handle_config(self, config, translateconfig):
        if (not translateconfig.help and
            translateconfig._cfgimpl_value_owners['opt'] == 'default'):
            raise Exception("You have to specify the --opt level.\n"
                    "Try --opt=2 or --opt=jit, or equivalently -O2 or -Ojit .")
        self.translateconfig = translateconfig
        # set up the objspace optimizations based on the --opt argument
        from pypy.config.pypyoption import set_pypy_opt_level
        set_pypy_opt_level(config, translateconfig.opt)

    def print_help(self, config):
        self.opt_parser(config).print_help()

    def get_additional_config_options(self):
        from pypy.config.pypyoption import pypy_optiondescription
        return pypy_optiondescription

    def target(self, driver, args):
        driver.exe_name = 'pypy-%(backend)s'

        config = driver.config
        parser = self.opt_parser(config)

        parser.parse_args(args)

        # expose the following variables to ease debugging
        global space, entry_point

        if config.objspace.allworkingmodules:
            from pypy.config.pypyoption import enable_allworkingmodules
            enable_allworkingmodules(config)
        if config.objspace.translationmodules:
            from pypy.config.pypyoption import enable_translationmodules
            enable_translationmodules(config)

        config.translation.suggest(check_str_without_nul=True)
        config.translation.suggest(shared=True)
        config.translation.suggest(icon=os.path.join(this_dir, 'pypy.ico'))
        if config.translation.shared:
            if config.translation.output is not None:
                raise Exception("Cannot use the --output option with PyPy "
                                "when --shared is on (it is by default). "
                                "See issue #1971.")
            if config.translation.profopt is not None:
                raise Exception("Cannot use the --profopt option "
                                "when --shared is on (it is by default). "
                                "See issue #2398.")
        if sys.platform == 'win32':
            libdir = thisdir.join('..', '..', 'libs')
            libdir.ensure(dir=1)
            config.translation.libname = str(libdir.join('python27.lib'))

        if config.translation.thread:
            config.objspace.usemodules.thread = True
        elif config.objspace.usemodules.thread:
            try:
                config.translation.thread = True
            except ConflictConfigError:
                # If --allworkingmodules is given, we reach this point
                # if threads cannot be enabled (e.g. they conflict with
                # something else).  In this case, we can try setting the
                # usemodules.thread option to False again.  It will
                # cleanly fail if that option was set to True by the
                # command-line directly instead of via --allworkingmodules.
                config.objspace.usemodules.thread = False

        if config.translation.continuation:
            config.objspace.usemodules._continuation = True
        elif config.objspace.usemodules._continuation:
            try:
                config.translation.continuation = True
            except ConflictConfigError:
                # Same as above: try to auto-disable the _continuation
                # module if translation.continuation cannot be enabled
                config.objspace.usemodules._continuation = False

        if not config.translation.rweakref:
            config.objspace.usemodules._weakref = False

        if config.translation.jit:
            config.objspace.usemodules.pypyjit = True
        elif config.objspace.usemodules.pypyjit:
            config.translation.jit = True

        if config.translation.sandbox:
            config.objspace.lonepycfiles = False

        config.translating = True

        import translate
        translate.log_config(config.objspace, "PyPy config object")

        # obscure hack to stuff the translation options into the translated PyPy
        import pypy.module.sys
        options = make_dict(config)
        wrapstr = 'space.wrap(%r)' % (options)
        pypy.module.sys.Module.interpleveldefs['pypy_translation_info'] = wrapstr
        if config.objspace.usemodules._cffi_backend:
            self.hack_for_cffi_modules(driver)

        return self.get_entry_point(config)

    def hack_for_cffi_modules(self, driver):
        # HACKHACKHACK
        # ugly hack to modify target goal from compile_* to build_cffi_imports
        # this should probably get cleaned up and merged with driver.create_exe
        from rpython.translator.driver import taskdef
        import types

        class Options(object):
            pass


        def mkexename(name):
            if sys.platform == 'win32':
                name = name.new(ext='exe')
            return name

        compile_goal, = driver.backend_select_goals(['compile'])
        @taskdef([compile_goal], "Create cffi bindings for modules")
        def task_build_cffi_imports(self):
            from pypy.tool.build_cffi_imports import create_cffi_import_libraries
            ''' Use cffi to compile cffi interfaces to modules'''
            exename = mkexename(driver.compute_exe_name())
            basedir = exename
            while not basedir.join('include').exists():
                _basedir = basedir.dirpath()
                if _basedir == basedir:
                    raise ValueError('interpreter %s not inside pypy repo',
                                     str(exename))
                basedir = _basedir
            modules = self.config.objspace.usemodules.getpaths()
            options = Options()
            # XXX possibly adapt options using modules
            failures = create_cffi_import_libraries(exename, options, basedir)
            # if failures, they were already printed
            print  >> sys.stderr, str(exename),'successfully built (errors, if any, while building the above modules are ignored)'
        driver.task_build_cffi_imports = types.MethodType(task_build_cffi_imports, driver)
        driver.tasks['build_cffi_imports'] = driver.task_build_cffi_imports, [compile_goal]
        driver.default_goal = 'build_cffi_imports'
        # HACKHACKHACK end

    def jitpolicy(self, driver):
        from pypy.module.pypyjit.policy import PyPyJitPolicy
        from pypy.module.pypyjit.hooks import pypy_hooks
        return PyPyJitPolicy(pypy_hooks)

    def get_entry_point(self, config):
        space = make_objspace(config)

        # manually imports app_main.py
        filename = os.path.join(pypydir, 'interpreter', 'app_main.py')
        app = gateway.applevel(open(filename).read(), 'app_main.py', 'app_main')
        app.hidden_applevel = False
        w_dict = app.getwdict(space)
        entry_point, _ = create_entry_point(space, w_dict)

        return entry_point, None, PyPyAnnotatorPolicy()

    def interface(self, ns):
        for name in ['take_options', 'handle_config', 'print_help', 'target',
                     'jitpolicy', 'get_entry_point',
                     'get_additional_config_options']:
            ns[name] = getattr(self, name)


PyPyTarget().interface(globals())

