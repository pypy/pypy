#include <stddef.h>

#define MAX_FUNC_NAME 1024

static int profile_file = -1;
static long prepare_interval_usec = 0;
static long profile_interval_usec = 0;
static int opened_profile(char *interp_name);

#define MARKER_STACKTRACE '\x01'
#define MARKER_VIRTUAL_IP '\x02'
#define MARKER_TRAILER '\x03'
#define MARKER_INTERP_NAME '\x04'   /* deprecated */
#define MARKER_HEADER '\x05'

#define VERSION_BASE '\x00'
#define VERSION_THREAD_ID '\x01'
#define VERSION_TAG '\x02'

#define MAX_STACK_DEPTH   \
    ((SINGLE_BUF_SIZE - sizeof(struct prof_stacktrace_s)) / sizeof(void *))

typedef struct prof_stacktrace_s {
    char padding[sizeof(long) - 1];
    char marker;
    long count, depth;
    intptr_t stack[];
} prof_stacktrace_s;


RPY_EXTERN
char *vmprof_init(int fd, double interval, char *interp_name)
{
    if (!(interval >= 1e-6 && interval < 1.0))   /* also if it is NaN */
        return "bad value for 'interval'";
    prepare_interval_usec = (int)(interval * 1000000.0);

    if (prepare_concurrent_bufs() < 0)
        return "out of memory";

    assert(fd >= 0);
    profile_file = fd;
    if (opened_profile(interp_name) < 0) {
        profile_file = -1;
        return strerror(errno);
    }
    return NULL;
}

static int _write_all(const char *buf, size_t bufsize);

static int opened_profile(char *interp_name)
{
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
    header.interp_name[2] = VERSION_TAG;
    header.interp_name[3] = namelen;
    memcpy(&header.interp_name[4], interp_name, namelen);
    return _write_all((char*)&header, 5 * sizeof(long) + 4 + namelen);
}

/* *************************************************************
 * functions to dump the stack trace
 * *************************************************************
 */


static int get_stack_trace(vmprof_stack_t* stack, intptr_t *result, int max_depth, intptr_t pc)
{
    int n = 0;
    intptr_t addr = 0;
    int bottom_jitted = 0;

    if (stack == NULL)
        return 0;

    // check if the pc is in JIT
#ifdef PYPY_JIT_CODEMAP
    if (pypy_find_codemap_at_addr((intptr_t)pc, &addr)) {
        // the bottom part is jitted, means we can fill up the first part
        // from the JIT
        n = vmprof_write_header_for_jit_addr(result, n, pc, max_depth);
        stack = stack->next; // skip the first item as it contains garbage
    }
#endif
    while (n < max_depth - 1 && stack) {
        if (stack->kind == VMPROF_CODE_TAG) {
            result[n] = stack->kind;
            result[n + 1] = stack->value;
            n += 2;
        }
#ifdef PYPY_JIT_CODEMAP
        else if (stack->kind == VMPROF_JITTED_TAG) {
            pc = ((intptr_t*)(stack->value - sizeof(intptr_t)))[0];
            n = vmprof_write_header_for_jit_addr(result, n, pc, max_depth);
        }
#endif
        stack = stack->next;
    }
    return n;
}

#ifndef RPYTHON_LL2CTYPES
static vmprof_stack_t *get_vmprof_stack(void)
{
    struct pypy_threadlocal_s *tl;
    _OP_THREADLOCALREF_ADDR_SIGHANDLER(tl);
    if (tl == NULL)
        return NULL;
    else
        return tl->vmprof_tl_stack;
}
#else
static vmprof_stack_t *get_vmprof_stack(void)
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
    intptr_t pc = ucontext ? GetPC((ucontext_t *)ucontext) : 0;
#endif
    if (stack == NULL)
        stack = get_vmprof_stack();
    n = get_stack_trace(stack, result_p, result_length - 2, pc);
    return (intptr_t)n;
}
