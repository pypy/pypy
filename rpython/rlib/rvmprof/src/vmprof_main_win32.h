
#include "windows.h"

HANDLE write_mutex;

int prepare_concurrent_bufs(void)
{
    if (!(write_mutex = CreateMutex(NULL, FALSE, NULL)))
        return -1;
    return 0;
}

#include "vmprof_stack.h"
#include "vmprof_common.h"
#include <tlhelp32.h>

// This file has been inspired (but not copied from since the LICENSE
// would not allow it) from verysleepy profiler

volatile int thread_started = 0;
volatile int enabled = 0;

static int _write_all(const char *buf, size_t bufsize)
{
    int res;
    res = WaitForSingleObject(write_mutex, INFINITE);
    if (profile_file == -1) {
        ReleaseMutex(write_mutex);
        return -1;
    }
    while (bufsize > 0) {
        ssize_t count = write(profile_file, buf, bufsize);
        if (count <= 0) {
            ReleaseMutex(write_mutex);
            return -1;   /* failed */
        }
        buf += count;
        bufsize -= count;
    }
    ReleaseMutex(write_mutex);
    return 0;
}

RPY_EXTERN
int vmprof_register_virtual_function(char *code_name, long code_uid,
                                     int auto_retry)
{
    char buf[2048];
    int namelen = strnlen(code_name, 1023);
    buf[0] = MARKER_VIRTUAL_IP;
    *(long*)(buf + 1) = code_uid;
    *(long*)(buf + 1 + sizeof(long)) = namelen;
    memcpy(buf + 1 + 2 * sizeof(long), code_name, namelen);
    _write_all(buf, namelen + 2 * sizeof(long) + 1);
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
    depth = read_trace_from_cpy_frame(tstate->frame, stack->stack,
        MAX_STACK_DEPTH);
    stack->depth = depth;
    stack->stack[depth++] = (void*)thread_id;
    stack->count = 1;
    stack->marker = MARKER_STACKTRACE;
    ResumeThread(hThread);
    return depth;
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
        tstate = PyInterpreterState_Head()->tstate_head;
        while (tstate) {
            depth = vmprof_snapshot_thread(tstate->thread_id, tstate, stack);
            if (depth > 0) {
                _write_all((char*)stack + offsetof(prof_stacktrace_s, marker),
                    depth * sizeof(void *) +
                        sizeof(struct prof_stacktrace_s) -
                        offsetof(struct prof_stacktrace_s, marker));
            }
            tstate = tstate->next;
        }
    }
}

RPY_EXTERN
int vmprof_enable(void)
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

    enabled = 0;
    if (_write_all(&marker, 1) < 0)
        return -1;
    profile_file = -1;
    return 0;
}

RPY_EXTERN
void vmprof_ignore_signals(int ignored)
{
}
