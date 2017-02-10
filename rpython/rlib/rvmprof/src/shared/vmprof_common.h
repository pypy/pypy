#pragma once

#include "vmprof.h"
#include "machine.h"
#include "compat.h"

#include <stddef.h>
#include <time.h>

#ifndef VMPROF_WINDOWS
#include <sys/time.h>
#include "vmprof_mt.h"
#endif

#define MAX_FUNC_NAME 1024

static long prepare_interval_usec = 0;
static long profile_interval_usec = 0;

static int opened_profile(const char *interp_name, int memory, int proflines, int native);

#ifdef VMPROF_UNIX
static struct profbuf_s *volatile current_codes;
#endif

#define MAX_STACK_DEPTH   \
    ((SINGLE_BUF_SIZE - sizeof(struct prof_stacktrace_s)) / sizeof(void *))

/*
 * NOTE SHOULD NOT BE DONE THIS WAY. Here is an example why:
 * assume the following struct content:
 * struct ... {
 *    char padding[sizeof(long) - 1];
 *    char marker;
 *    long count, depth;
 *    void *stack[];
 * }
 *
 * Here a table of the offsets on a 64 bit machine:
 * field  | GCC | VSC (windows)
 * ---------------------------
 * marker |   7 |   3
 * count  |   8 |   4
 * depth  |  16 |   8
 * stack  |  24 |   16 (VSC adds 4 padding byte hurray!)
 *
 * This means that win32 worked by chance (because sizeof(void*)
 * is 4, but fails on win32
 */
typedef struct prof_stacktrace_s {
    char padding[sizeof(long) - 1];
    char marker;
    long count, depth;
    void *stack[];
} prof_stacktrace_s;

#define SIZEOF_PROF_STACKTRACE sizeof(long)+sizeof(long)+sizeof(char)

RPY_EXTERN
char *vmprof_init(int fd, double interval, int memory,
                  int proflines, const char *interp_name, int native)
{
    if (!(interval >= 1e-6 && interval < 1.0)) {   /* also if it is NaN */
        return "bad value for 'interval'";
    }
    prepare_interval_usec = (int)(interval * 1000000.0);

    if (prepare_concurrent_bufs() < 0)
        return "out of memory";
#if VMPROF_UNIX
    current_codes = NULL;
#else
    if (memory) {
        return "memory tracking only supported on unix";
    }
    if (native) {
        return "native profiling only supported on unix";
    }
#endif
    assert(fd >= 0);
    vmp_set_profile_fileno(fd);
    if (opened_profile(interp_name, memory, proflines, native) < 0) {
        vmp_set_profile_fileno(0);
        return strerror(errno);
    }
    return NULL;
}

static int opened_profile(const char *interp_name, int memory, int proflines, int native)
{
    int success;
    int bits;
    struct {
        long hdr[5];
        char interp_name[259];
    } header;

    size_t namelen = strnlen(interp_name, 255);

    header.hdr[0] = 0;
    header.hdr[1] = 3;
    header.hdr[2] = 0;
    header.hdr[3] = prepare_interval_usec;
    header.hdr[4] = 0;
    header.interp_name[0] = MARKER_HEADER;
    header.interp_name[1] = '\x00';
    header.interp_name[2] = VERSION_TIMESTAMP;
    header.interp_name[3] = memory*PROFILE_MEMORY + proflines*PROFILE_LINES + \
                            native*PROFILE_NATIVE;
#ifdef RPYTHON_VMPROF
    header.interp_name[3] += PROFILE_RPYTHON;
#endif
    header.interp_name[4] = (char)namelen;

    memcpy(&header.interp_name[5], interp_name, namelen);
    success = vmp_write_all((char*)&header, 5 * sizeof(long) + 5 + namelen);
    if (success < 0) {
        return success;
    }

    /* Write the time and the zone to the log file, profiling will start now */
    (void)vmp_write_time_now(MARKER_TIME_N_ZONE);

    /* write some more meta information */
    vmp_write_meta("os", vmp_machine_os_name());
    bits = vmp_machine_bits();
    if (bits == 64) {
        vmp_write_meta("bits", "64");
    } else if (bits == 32) {
        vmp_write_meta("bits", "32");
    }

    return success;
}


/* Seems that CPython 3.5.1 made our job harder.  Did not find out how
   to do that without these hacks.  We can't use PyThreadState_GET(),
   because that calls PyThreadState_Get() which fails an assert if the
   result is NULL. */
#if PY_MAJOR_VERSION >= 3 && !defined(_Py_atomic_load_relaxed)
                             /* this was abruptly un-defined in 3.5.1 */
void *volatile _PyThreadState_Current;
   /* XXX simple volatile access is assumed atomic */
#  define _Py_atomic_load_relaxed(pp)  (*(pp))
#endif

#ifdef RPYTHON_VMPROF
#ifndef RPYTHON_LL2CTYPES
static PY_STACK_FRAME_T *get_vmprof_stack(void)
{
    struct pypy_threadlocal_s *tl;
    _OP_THREADLOCALREF_ADDR_SIGHANDLER(tl);
    if (tl == NULL)
        return NULL;
    else
        return tl->vmprof_tl_stack;
}
#else
static PY_STACK_FRAME_T *get_vmprof_stack(void)
{
    return 0;
}
#endif

RPY_EXTERN
intptr_t vmprof_get_traceback(void *stack, void *ucontext,
                              intptr_t *result_p, intptr_t result_length)
{
    int n;
#ifdef _WIN32
    intptr_t pc = 0;   /* XXX implement me */
#else
    intptr_t pc = ucontext ? (intptr_t)GetPC((ucontext_t *)ucontext) : 0;
#endif
    if (stack == NULL) {
        stack = get_vmprof_stack();
    }
    int enabled = vmp_native_enabled();
    vmp_native_disable();
    n = get_stack_trace(stack, result_p, result_length - 2, pc);
    if (enabled) {
        vmp_native_enable();
    }
    return (intptr_t)n;
}
#endif
