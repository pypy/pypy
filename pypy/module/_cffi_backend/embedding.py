import os
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo

from pypy.interpreter.error import OperationError, oefmt

# ____________________________________________________________


EMBED_VERSION_MIN    = 0xB011
EMBED_VERSION_MAX    = 0xB0FF

STDERR = 2
INITSTRUCTPTR = lltype.Ptr(lltype.Struct('CFFI_INIT',
                                         ('name', rffi.CCHARP),
                                         ('func', rffi.VOIDP),
                                         ('code', rffi.CCHARP)))

def load_embedded_cffi_module(space, version, init_struct):
    from pypy.module._cffi_backend.cffi1_module import load_cffi1_module
    declare_c_function()     # translation-time hint only:
                             # declare _cffi_carefully_make_gil()
    #
    version = rffi.cast(lltype.Signed, version)
    if not (EMBED_VERSION_MIN <= version <= EMBED_VERSION_MAX):
        raise oefmt(space.w_ImportError,
            "cffi embedded module has got unknown version tag %s",
            hex(version))
    #
    if space.config.objspace.usemodules.thread:
        from pypy.module.thread import os_thread
        os_thread.setup_threads(space)
    #
    name = rffi.charp2str(init_struct.name)
    load_cffi1_module(space, name, None, init_struct.func)
    code = rffi.charp2str(init_struct.code)
    compiler = space.createcompiler()
    pycode = compiler.compile(code, "<init code for '%s'>" % name, 'exec', 0)
    w_globals = space.newdict(module=True)
    space.setitem_str(w_globals, "__builtins__", space.wrap(space.builtin))
    pycode.exec_code(space, w_globals, w_globals)


class Global:
    pass
glob = Global()

def patch_sys(space):
    # Annoying: CPython would just use the C-level std{in,out,err} as
    # configured by the main application, for example in binary mode
    # on Windows or with buffering turned off.  We can't easily do the
    # same.  Instead, go for the safest bet (but possibly bad for
    # performance) and open sys.std{in,out,err} unbuffered.  On
    # Windows I guess binary mode is a better default choice.
    #
    # XXX if needed, we could add support for a flag passed to
    # pypy_init_embedded_cffi_module().
    if not glob.patched_sys:
        space.appexec([], """():
            import os, sys
            sys.stdin  = sys.__stdin__  = os.fdopen(0, 'rb', 0)
            sys.stdout = sys.__stdout__ = os.fdopen(1, 'wb', 0)
            sys.stderr = sys.__stderr__ = os.fdopen(2, 'wb', 0)
        """)
        glob.patched_sys = True


def pypy_init_embedded_cffi_module(version, init_struct):
    # called from __init__.py
    name = "?"
    try:
        init_struct = rffi.cast(INITSTRUCTPTR, init_struct)
        name = rffi.charp2str(init_struct.name)
        #
        space = glob.space
        must_leave = False
        try:
            must_leave = space.threadlocals.try_enter_thread(space)
            patch_sys(space)
            load_embedded_cffi_module(space, version, init_struct)
            res = 0
        except OperationError as operr:
            operr.write_unraisable(space, "initialization of '%s'" % name,
                                   with_traceback=True)
            space.appexec([], r"""():
                import sys
                sys.stderr.write('pypy version: %s.%s.%s\n' %
                                 sys.pypy_version_info[:3])
                sys.stderr.write('sys.path: %r\n' % (sys.path,))
            """)
            res = -1
        if must_leave:
            space.threadlocals.leave_thread(space)
    except Exception as e:
        # oups! last-level attempt to recover.
        try:
            os.write(STDERR, "From initialization of '")
            os.write(STDERR, name)
            os.write(STDERR, "':\n")
            os.write(STDERR, str(e))
            os.write(STDERR, "\n")
        except:
            pass
        res = -1
    return rffi.cast(rffi.INT, res)

# ____________________________________________________________

if os.name == 'nt':

    do_includes = r"""
#define _WIN32_WINNT 0x0501
#include <windows.h>

#define CFFI_INIT_HOME_PATH_MAX  _MAX_PATH
static void _cffi_init(void);
static void _cffi_init_error(const char *msg, const char *extra);

static int _cffi_init_home(char *output_home_path)
{
    HMODULE hModule = 0;
    DWORD res;

    GetModuleHandleEx(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | 
                       GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       (LPCTSTR)&_cffi_init, &hModule);

    if (hModule == 0 ) {
        _cffi_init_error("GetModuleHandleEx() failed", "");
        return -1;
    }
    res = GetModuleFileName(hModule, output_home_path, CFFI_INIT_HOME_PATH_MAX);
    if (res >= CFFI_INIT_HOME_PATH_MAX) {
        return -1;
    }
    return 0;
}

static void _cffi_init_once(void)
{
    static LONG volatile lock = 0;
    static int _init_called = 0;

    while (InterlockedCompareExchange(&lock, 1, 0) != 0) {
         SwitchToThread();        /* spin loop */
    }
    if (!_init_called) {
        _cffi_init();
        _init_called = 1;
    }
    InterlockedCompareExchange(&lock, 0, 1);
}
"""

else:

    do_includes = r"""
#include <dlfcn.h>
#include <pthread.h>

#define CFFI_INIT_HOME_PATH_MAX  PATH_MAX
static void _cffi_init(void);
static void _cffi_init_error(const char *msg, const char *extra);

static int _cffi_init_home(char *output_home_path)
{
    Dl_info info;
    dlerror();   /* reset */
    if (dladdr(&_cffi_init, &info) == 0) {
        _cffi_init_error("dladdr() failed: ", dlerror());
        return -1;
    }
    if (realpath(info.dli_fname, output_home_path) == NULL) {
        perror("realpath() failed");
        _cffi_init_error("realpath() failed", "");
        return -1;
    }
    return 0;
}

static void _cffi_init_once(void)
{
    static pthread_once_t once_control = PTHREAD_ONCE_INIT;
    pthread_once(&once_control, _cffi_init);
}
"""

do_startup = do_includes + r"""
RPY_EXPORTED void rpython_startup_code(void);
RPY_EXPORTED int pypy_setup_home(char *, int);

static unsigned char _cffi_ready = 0;
static const char *volatile _cffi_module_name;

static void _cffi_init_error(const char *msg, const char *extra)
{
    fprintf(stderr,
            "\nPyPy initialization failure when loading module '%s':\n%s%s\n",
            _cffi_module_name, msg, extra);
}

static void _cffi_init(void)
{
    char home[CFFI_INIT_HOME_PATH_MAX + 1];

    rpython_startup_code();
    RPyGilAllocate();

    if (_cffi_init_home(home) != 0)
        return;
    if (pypy_setup_home(home, 1) != 0) {
        _cffi_init_error("pypy_setup_home() failed", "");
        return;
    }
    _cffi_ready = 1;
}

RPY_EXPORTED
int pypy_carefully_make_gil(const char *name)
{
    /* For CFFI: this initializes the GIL and loads the home path.
       It can be called completely concurrently from unrelated threads.
       It assumes that we don't hold the GIL before (if it exists), and we
       don't hold it afterwards.
    */
    _cffi_module_name = name;    /* not really thread-safe, but better than
                                    nothing */
    _cffi_init_once();
    return (int)_cffi_ready - 1;
}
"""
eci = ExternalCompilationInfo(separate_module_sources=[do_startup])

declare_c_function = rffi.llexternal_use_eci(eci)
