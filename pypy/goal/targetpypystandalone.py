import py

import os, sys

import pypy
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.tool.ann_override import PyPyAnnotatorPolicy
from rpython.config.config import to_optparse, make_dict, SUPPRESS_USAGE
from rpython.config.config import ConflictConfigError
from pypy.tool.option import make_objspace
from pypy.conftest import pypydir
from rpython.rlib import rthread
from pypy.module.thread import os_thread

thisdir = py.path.local(__file__).dirpath()

try:
    this_dir = os.path.dirname(__file__)
except NameError:
    this_dir = os.path.dirname(sys.argv[0])

def debug(msg):
    os.write(2, "debug: " + msg + '\n')

# __________  Entry point  __________


def create_entry_point(space, w_dict):
    if w_dict is not None: # for tests
        w_entry_point = space.getitem(w_dict, space.wrap('entry_point'))
        w_run_toplevel = space.getitem(w_dict, space.wrap('run_toplevel'))
        w_call_finish_gateway = space.wrap(gateway.interp2app(call_finish))
        w_call_startup_gateway = space.wrap(gateway.interp2app(call_startup))
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
                space.call_function(w_run_toplevel, w_call_startup_gateway)
                w_executable = space.wrap(argv[0])
                w_argv = space.newlist([space.wrap(s) for s in argv[1:]])
                w_exitcode = space.call_function(w_entry_point, w_executable, w_argv)
                exitcode = space.int_w(w_exitcode)
                # try to pull it all in
            ##    from pypy.interpreter import main, interactive, error
            ##    con = interactive.PyPyConsole(space)
            ##    con.interact()
            except OperationError, e:
                debug("OperationError:")
                debug(" operror-type: " + e.w_type.getname(space))
                debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
                return 1
        finally:
            try:
                space.call_function(w_run_toplevel, w_call_finish_gateway)
            except OperationError, e:
                debug("OperationError:")
                debug(" operror-type: " + e.w_type.getname(space))
                debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
                return 1
        return exitcode

    # register the minimal equivalent of running a small piece of code. This
    # should be used as sparsely as possible, just to register callbacks

    from rpython.rlib.entrypoint import entrypoint, RPython_StartupCode
    from rpython.rtyper.lltypesystem import rffi, lltype
    from rpython.rtyper.lltypesystem.lloperation import llop

    w_pathsetter = space.appexec([], """():
    def f(path):
        import sys
        sys.path[:] = path
    return f
    """)

    @entrypoint('main', [rffi.CCHARP, rffi.INT], c_name='pypy_setup_home')
    def pypy_setup_home(ll_home, verbose):
        from pypy.module.sys.initpath import pypy_find_stdlib
        verbose = rffi.cast(lltype.Signed, verbose)
        if ll_home:
            home = rffi.charp2str(ll_home)
        else:
            home = pypydir
        w_path = pypy_find_stdlib(space, home)
        if space.is_none(w_path):
            if verbose:
                debug("Failed to find library based on pypy_find_stdlib")
            return 1
        space.startup()
        space.call_function(w_pathsetter, w_path)
        # import site
        try:
            import_ = space.getattr(space.getbuiltinmodule('__builtin__'),
                                    space.wrap('__import__'))
            space.call_function(import_, space.wrap('site'))
            return 0
        except OperationError, e:
            if verbose:
                debug("OperationError:")
                debug(" operror-type: " + e.w_type.getname(space))
                debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
            return -1

    @entrypoint('main', [rffi.CCHARP], c_name='pypy_execute_source')
    def pypy_execute_source(ll_source):
        after = rffi.aroundstate.after
        if after: after()
        source = rffi.charp2str(ll_source)
        res = _pypy_execute_source(source)
        before = rffi.aroundstate.before
        if before: before()
        return rffi.cast(rffi.INT, res)

    @entrypoint('main', [rffi.CCHARP, lltype.Signed],
                c_name='pypy_execute_source_ptr')
    def pypy_execute_source_ptr(ll_source, ll_ptr):
        after = rffi.aroundstate.after
        if after: after()
        source = rffi.charp2str(ll_source)
        space.setitem(w_globals, space.wrap('c_argument'),
                      space.wrap(ll_ptr))
        res = _pypy_execute_source(source)
        before = rffi.aroundstate.before
        if before: before()
        return rffi.cast(rffi.INT, res)        

    @entrypoint('main', [], c_name='pypy_init_threads')
    def pypy_init_threads():
        if not space.config.objspace.usemodules.thread:
            return
        os_thread.setup_threads(space)
        before = rffi.aroundstate.before
        if before: before()

    @entrypoint('main', [], c_name='pypy_thread_attach')
    def pypy_thread_attach():
        if not space.config.objspace.usemodules.thread:
            return
        os_thread.setup_threads(space)
        os_thread.bootstrapper.acquire(space, None, None)
        rthread.gc_thread_start()
        os_thread.bootstrapper.nbthreads += 1
        os_thread.bootstrapper.release()
        before = rffi.aroundstate.before
        if before: before()

    w_globals = space.newdict()
    space.setitem(w_globals, space.wrap('__builtins__'),
                  space.builtin_modules['__builtin__'])

    def _pypy_execute_source(source):
        try:
            compiler = space.createcompiler()
            stmt = compiler.compile(source, 'c callback', 'exec', 0)
            stmt.exec_code(space, w_globals, w_globals)
        except OperationError, e:
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

def call_finish(space):
    space.finish()

def call_startup(space):
    space.startup()

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

        # as of revision 27081, multimethod.py uses the InstallerVersion1 by default
        # because it is much faster both to initialize and run on top of CPython.
        # The InstallerVersion2 is optimized for making a translator-friendly
        # structure for low level backends. However, InstallerVersion1 is still
        # preferable for high level backends, so we patch here.

        from pypy.objspace.std import multimethod
        if config.objspace.std.multimethods == 'mrd':
            assert multimethod.InstallerVersion1.instance_counter == 0,\
                   'The wrong Installer version has already been instatiated'
            multimethod.Installer = multimethod.InstallerVersion2
        elif config.objspace.std.multimethods == 'doubledispatch':
            # don't rely on the default, set again here
            assert multimethod.InstallerVersion2.instance_counter == 0,\
                   'The wrong Installer version has already been instatiated'
            multimethod.Installer = multimethod.InstallerVersion1

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
            config.objspace.usepycfiles = False

        config.translating = True

        import translate
        translate.log_config(config.objspace, "PyPy config object")

        # obscure hack to stuff the translation options into the translated PyPy
        import pypy.module.sys
        options = make_dict(config)
        wrapstr = 'space.wrap(%r)' % (options)
        pypy.module.sys.Module.interpleveldefs['pypy_translation_info'] = wrapstr

        return self.get_entry_point(config)

    def jitpolicy(self, driver):
        from pypy.module.pypyjit.policy import PyPyJitPolicy, pypy_hooks
        return PyPyJitPolicy(pypy_hooks)

    def get_entry_point(self, config):
        from pypy.tool.lib_pypy import import_from_lib_pypy
        rebuild = import_from_lib_pypy('ctypes_config_cache/rebuild')
        rebuild.try_rebuild()

        space = make_objspace(config)

        # manually imports app_main.py
        filename = os.path.join(pypydir, 'interpreter', 'app_main.py')
        app = gateway.applevel(open(filename).read(), 'app_main.py', 'app_main')
        app.hidden_applevel = False
        w_dict = app.getwdict(space)
        entry_point, _ = create_entry_point(space, w_dict)

        return entry_point, None, PyPyAnnotatorPolicy(single_space = space)

    def interface(self, ns):
        for name in ['take_options', 'handle_config', 'print_help', 'target',
                     'jitpolicy', 'get_entry_point',
                     'get_additional_config_options']:
            ns[name] = getattr(self, name)


PyPyTarget().interface(globals())

