#pragma once

#include "windows.h"
#include "compat.h"
#include "vmp_stack.h"

HANDLE write_mutex;

int prepare_concurrent_bufs(void);

#include "vmprof_common.h"
#include <tlhelp32.h>

// This file has been inspired (but not copied from since the LICENSE
// would not allow it) from verysleepy profiler

volatile int thread_started = 0;
volatile int enabled = 0;

int vmp_write_all(const char *buf, size_t bufsize);

RPY_EXTERN
int vmprof_register_virtual_function(char *code_name, intptr_t code_uid,
                                     int auto_retry)
{
    char buf[2048];
    long namelen;

    namelen = (long)strnlen(code_name, 1023);
    buf[0] = MARKER_VIRTUAL_IP;
    *(intptr_t*)(buf + 1) = code_uid;
    *(long*)(buf + 1 + sizeof(intptr_t)) = namelen;
    memcpy(buf + 1 + sizeof(intptr_t) + sizeof(long), code_name, namelen);
    vmp_write_all(buf, 1 + sizeof(intptr_t) + sizeof(long) + namelen);
    return 0;
}

int vmprof_snapshot_thread(DWORD thread_id, PyThreadState *tstate, prof_stacktrace_s *stack)
{
    HRESULT result;
    HANDLE hThread = OpenThread(THREAD_ALL_ACCESS, FALSE, thread_id);
    int depth;
    if (!hThread) {
        return -1;
    }
    result = SuspendThread(hThread);
    if(result == 0xffffffff)
        return -1; // possible, e.g. attached debugger or thread alread suspended
    // find the correct thread
    depth = vmp_walk_and_record_stack(tstate->frame, stack->stack,
                                      MAX_STACK_DEPTH, 0);
    stack->depth = depth;
    stack->stack[depth++] = (void*)thread_id;
    stack->count = 1;
    stack->marker = MARKER_STACKTRACE;
    ResumeThread(hThread);
    return depth;
}

static
PyThreadState * get_current_thread_state(void)
{
#if PY_MAJOR_VERSION < 3
    return _PyThreadState_Current;
#elif PY_VERSION_HEX < 0x03050200
    return (PyThreadState*) _Py_atomic_load_relaxed(&_PyThreadState_Current);
#else
    return _PyThreadState_UncheckedGet();
#endif
}

long __stdcall vmprof_mainloop(void *arg)
{   
    prof_stacktrace_s *stack = (prof_stacktrace_s*)malloc(SINGLE_BUF_SIZE);
    HANDLE hThreadSnap = INVALID_HANDLE_VALUE; 
    int depth;
    PyThreadState *tstate;

    while (1) {
        Sleep(profile_interval_usec * 1000);
        if (!enabled) {
            continue;
        }
        tstate = get_current_thread_state();
        if (!tstate)
            continue;
        depth = vmprof_snapshot_thread(tstate->thread_id, tstate, stack);
        if (depth > 0) {
            // see note in vmprof_common.h on the prof_stacktrace_s struct why
            // there are two vmpr_write_all calls
            vmp_write_all((char*)stack + offsetof(prof_stacktrace_s, marker), SIZEOF_PROF_STACKTRACE);
            vmp_write_all((char*)stack->stack, depth * sizeof(void*));
        }
    }
}

RPY_EXTERN
int vmprof_enable(int memory)
{
    if (!thread_started) {
        if (!CreateThread(NULL, 0, vmprof_mainloop, NULL, 0, NULL)) {
            return -1;
        }
        thread_started = 1;
    }
    enabled = 1;
    return 0;
}

RPY_EXTERN
int vmprof_disable(void)
{
    char marker = MARKER_TRAILER;
    (void)vmp_write_time_now(MARKER_TRAILER);

    enabled = 0;
    vmp_set_profile_fileno(-1);
    return 0;
}

RPY_EXTERN
void vmprof_ignore_signals(int ignored)
{
}
