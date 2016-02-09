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
    void *stack[];
} prof_stacktrace_s;


RPY_EXTERN
char *vmprof_init(int fd, double interval, char *interp_name)
{
    if (interval < 1e-6 || interval >= 1.0)
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

#ifndef RPYTHON_LL2CTYPES
static vmprof_stack_t *get_vmprof_stack(void)
{
    return RPY_THREADLOCALREF_GET(vmprof_tl_stack);
}
#else
static vmprof_stack_t *get_vmprof_stack(void)
{
    return 0;
}
#endif
