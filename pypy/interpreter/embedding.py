from rpython.rlib.entrypoint import entrypoint_highlevel
from rpython.rtyper.lltypesystem import rffi, lltype

w_pathsetter = space.appexec([], """():
def f(path):
    import sys
    sys.path[:] = path
return f
""")

@entrypoint_highlevel('main', [rffi.CCHARP, rffi.INT],
                      c_name='pypy_setup_home')
def pypy_setup_home(ll_home, verbose):
    from pypy.module.sys.initpath import pypy_find_stdlib
    _declare_c_function()
    verbose = rffi.cast(lltype.Signed, verbose)
    if ll_home:
        home1 = rffi.charp2str(ll_home)
        home = os.path.join(home1, 'x') # <- so that 'll_home' can be
                                        # directly the root directory
    else:
        home = home1 = pypydir
    w_path = pypy_find_stdlib(space, home)
    if space.is_none(w_path):
        if verbose:
            debug("pypy_setup_home: directories 'lib-python' and 'lib_pypy'"
                  " not found in '%s' or in any parent directory" % home1)
        return rffi.cast(rffi.INT, 1)
    space.startup()
    space.call_function(w_pathsetter, w_path)
    # import site
    try:
        space.setattr(space.getbuiltinmodule('sys'),
                      space.wrap('executable'),
                      space.wrap(home))
        import_ = space.getattr(space.getbuiltinmodule('__builtin__'),
                                space.wrap('__import__'))
        space.call_function(import_, space.wrap('site'))
        return rffi.cast(rffi.INT, 0)
    except OperationError, e:
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
    except OperationError, e:
        debug("OperationError:")
        debug(" operror-type: " + e.w_type.getname(space))
        debug(" operror-value: " + space.str_w(space.str(e.get_w_value(space))))
        return -1
    return 0


entrypoints_dict = {'pypy_execute_source': pypy_execute_source,
                    'pypy_execute_source_ptr': pypy_execute_source_ptr,
                    'pypy_init_threads': pypy_init_threads,
                    'pypy_thread_attach': pypy_thread_attach,
                    'pypy_setup_home': pypy_setup_home}


_declare_c_function = rffi.llexternal_use_eci(separate_module_sources=[
"""
#define PYPY_INIT_NO_THREADS   0x01
#define PYPY_INIT_QUIET        0x02

static int _pypy_init_result = -1;
static void _pypy_init_once_quiet(void);
static void _pypy_init_once_verbose(void);


#ifndef _MSC_VER   /* --- Posix version --- */

static char *guess_home(void)
{
    Dl_info info;
    if (dladdr(&guess_home, &info) == 0)
        return NULL;
    return realpath(info.dli_fname, NULL);
}

RPY_EXPORTED
int pypy_initialize(int flags)
{
    static pthread_once_t once_control_1 = PTHREAD_ONCE_INIT;
    static pthread_once_t once_control_2 = PTHREAD_ONCE_INIT;

    pthread_once(&once_control_1,
                 (flags & PYPY_INIT_QUIET) ? _pypy_init_once_quiet
                                           : _pypy_init_once_verbose);

    if (_pypy_init_result == 0 && (flags & PYPY_INIT_NO_THREADS) == 0)
        pthread_once(&once_control_2, pypy_init_threads);

    return _pypy_init_result;
}

#else            /* --- Windows version --- */

   XXX

#endif


static void _pypy_init_once(int verbose)
{
    char *home;
    int verbose;
    rpython_startup_code();

    home = guess_home();
    if (home == NULL)
        return;
    _pypy_init_result = pypy_setup_home(home, verbose);
    free(home);
}

static void _pypy_init_once_quiet(void)
{
    _pypy_init_once(0);
}

static void _pypy_init_once_verbose(void)
{
    _pypy_init_once(1);
}
"""
])
