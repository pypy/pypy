from rpython.rtyper.lltypesystem import rffi


declare_c_function = rffi.llexternal_use_eci(separate_module_sources=[
"""
/* XXX Windows missing */
#include <stdio.h>
#include <dlfcn.h>
#include <pthread.h>

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
    Dl_info info;
    char *home;

    rpython_startup_code();

    if (dladdr(&_cffi_init, &info) == 0) {
        _cffi_init_error("dladdr() failed: ", dlerror());
        return;
    }
    home = realpath(info.dli_fname, NULL);
    if (pypy_setup_home(home, 1) != 0) {
        _cffi_init_error("pypy_setup_home() failed", "");
        return;
    }

    RPyGilAllocate();
    RPyGilRelease();
    _cffi_ready = 1;
}

RPY_EXPORTED
int _cffi_carefully_make_gil(const char *name)
{
    /* For CFFI: this initializes the GIL and loads the home path.
       It can be called completely concurrently from unrelated threads.
       It assumes that we don't hold the GIL before (if it exists), and we
       don't hold it afterwards.
    */
    static pthread_once_t once_control = PTHREAD_ONCE_INIT;

    _cffi_module_name = name;    /* not really thread-safe, but better than
                                    nothing */
    pthread_once(&once_control, _cffi_init);
    return (int)_cffi_ready - 1;
}
"""])
