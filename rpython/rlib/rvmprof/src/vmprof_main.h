/* VMPROF
 *
 * statistical sampling profiler specifically designed to profile programs
 * which run on a Virtual Machine and/or bytecode interpreter, such as Python,
 * etc.
 *
 * The logic to dump the C stack traces is partly stolen from the code in
 * gperftools.
 * The file "getpc.h" has been entirely copied from gperftools.
 *
 * Tested only on gcc, linux, x86_64.
 *
 * Copyright (C) 2014-2015
 *   Antonio Cuni - anto.cuni@gmail.com
 *   Maciej Fijalkowski - fijall@gmail.com
 *   Armin Rigo - arigo@tunes.org
 *
 */

#define _GNU_SOURCE 1

#include <dlfcn.h>
#include <assert.h>
#include <pthread.h>
#include <sys/time.h>
#include <errno.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/types.h>
#include <signal.h>
#include <sys/stat.h>
#include <fcntl.h>
#include "vmprof_getpc.h"
#include "vmprof_unwind.h"
#include "vmprof_mt.h"


/************************************************************/

// functions copied from libunwind using dlopen

static int (*unw_get_reg)(unw_cursor_t*, int, unw_word_t*) = NULL;
static int (*unw_step)(unw_cursor_t*) = NULL;
static int (*unw_init_local)(unw_cursor_t *, unw_context_t *) = NULL;
static int (*unw_get_proc_info)(unw_cursor_t *, unw_proc_info_t *) = NULL;

static int profile_file = -1;
static long prepare_interval_usec;
static struct profbuf_s *volatile current_codes;
static void *(*mainloop_get_virtual_ip)(char *) = 0;

static int opened_profile(char *interp_name);
static void flush_codes(void);

#ifdef __APPLE__
#define UNWIND_NAME "/usr/lib/system/libunwind.dylib"
#define UNW_PREFIX "unw"
#else
#define UNWIND_NAME "libunwind.so"
#define UNW_PREFIX "_ULx86_64"
#endif

RPY_EXTERN
char *vmprof_init(int fd, double interval, char *interp_name)
{
    if (interval < 1e-6 || interval >= 1.0)
        return "bad value for 'interval'";
    prepare_interval_usec = (int)(interval * 1000000.0);

    if (!unw_get_reg) {
        void *libhandle;

        if (!(libhandle = dlopen(UNWIND_NAME, RTLD_LAZY | RTLD_LOCAL)))
            goto error;
        if (!(unw_get_reg = dlsym(libhandle, UNW_PREFIX "_get_reg")))
            goto error;
        if (!(unw_get_proc_info = dlsym(libhandle, UNW_PREFIX "_get_proc_info")))
            goto error;
        if (!(unw_init_local = dlsym(libhandle, UNW_PREFIX  "_init_local")))
            goto error;
        if (!(unw_step = dlsym(libhandle, UNW_PREFIX  "_step")))
            goto error;
    }
    if (prepare_concurrent_bufs() < 0)
        return "out of memory";

    assert(fd >= 0);
    profile_file = fd;
    if (opened_profile(interp_name) < 0) {
        profile_file = -1;
        return strerror(errno);
    }
    return NULL;

 error:
    return dlerror();
}

/************************************************************/

/* value: last bit is 1 if signals must be ignored; all other bits
   are a counter for how many threads are currently in a signal handler */
static long volatile signal_handler_value = 1;

RPY_EXTERN
void vmprof_ignore_signals(int ignored)
{
    if (!ignored) {
        __sync_fetch_and_and(&signal_handler_value, ~1L);
    }
    else {
        /* set the last bit, and wait until concurrently-running signal
           handlers finish */
        while (__sync_or_and_fetch(&signal_handler_value, 1L) != 1L) {
            usleep(1);
        }
    }
}


/* *************************************************************
 * functions to write a profile file compatible with gperftools
 * *************************************************************
 */

#define MAX_FUNC_NAME 128
#define MAX_STACK_DEPTH   \
    ((SINGLE_BUF_SIZE - sizeof(struct prof_stacktrace_s)) / sizeof(void *))

#define MARKER_STACKTRACE '\x01'
#define MARKER_VIRTUAL_IP '\x02'
#define MARKER_TRAILER '\x03'
#define MARKER_INTERP_NAME '\x04'   /* deprecated */
#define MARKER_HEADER '\x05'

#define VERSION_BASE '\x00'
#define VERSION_THREAD_ID '\x01'

struct prof_stacktrace_s {
    char padding[sizeof(long) - 1];
    char marker;
    long count, depth;
    void *stack[];
};

static long profile_interval_usec = 0;
static char atfork_hook_installed = 0;


/* ******************************************************
 * libunwind workaround for process JIT frames correctly
 * ******************************************************
 */

#include "vmprof_get_custom_offset.h"

typedef struct {
    void* _unused1;
    void* _unused2;
    void* sp;
    void* ip;
    void* _unused3[sizeof(unw_cursor_t)/sizeof(void*) - 4];
} vmprof_hacked_unw_cursor_t;

static int vmprof_unw_step(unw_cursor_t *cp, int first_run)
{
    void* ip;
    void* sp;
    ptrdiff_t sp_offset;
    unw_get_reg (cp, UNW_REG_IP, (unw_word_t*)&ip);
    unw_get_reg (cp, UNW_REG_SP, (unw_word_t*)&sp);
    if (!first_run) {
        // make sure we're pointing to the CALL and not to the first
        // instruction after. If the callee adjusts the stack for us
        // it's not safe to be at the instruction after
        ip -= 1;
    }
    sp_offset = vmprof_unw_get_custom_offset(ip, cp);

    if (sp_offset == -1) {
        // it means that the ip is NOT in JITted code, so we can use the
        // stardard unw_step
        return unw_step(cp);
    }
    else {
        // this is a horrible hack to manually walk the stack frame, by
        // setting the IP and SP in the cursor
        vmprof_hacked_unw_cursor_t *cp2 = (vmprof_hacked_unw_cursor_t*)cp;
        void* bp = (void*)sp + sp_offset;
        cp2->sp = bp;
        bp -= sizeof(void*);
        cp2->ip = ((void**)bp)[0];
        // the ret is on the top of the stack minus WORD
        return 1;
    }
}


/* *************************************************************
 * functions to dump the stack trace
 * *************************************************************
 */

static int get_stack_trace(void** result, int max_depth, ucontext_t *ucontext)
{
    void *ip;
    int n = 0;
    unw_cursor_t cursor;
    unw_context_t uc = *ucontext;

    int ret = unw_init_local(&cursor, &uc);
    assert(ret >= 0);
    (void)ret;

    while (n < max_depth) {
        if (unw_get_reg(&cursor, UNW_REG_IP, (unw_word_t *) &ip) < 0) {
            break;
        }

        unw_proc_info_t pip;
        unw_get_proc_info(&cursor, &pip);

        /* if n==0, it means that the signal handler interrupted us while we
           were in the trampoline, so we are not executing (yet) the real main
           loop function; just skip it */
        if (VMPROF_ADDR_OF_TRAMPOLINE((void*)pip.start_ip) && n > 0) {
            // found main loop stack frame
            void* sp;
            unw_get_reg(&cursor, UNW_REG_SP, (unw_word_t *) &sp);
            if (mainloop_get_virtual_ip)
                ip = mainloop_get_virtual_ip((char *)sp);
            else
                ip = *(void **)sp;
        }

        int first_run = (n == 0);
        result[n++] = ip;
        n = vmprof_write_header_for_jit_addr(result, n, ip, max_depth);
        if (vmprof_unw_step(&cursor, first_run) <= 0)
            break;
    }
    return n;
}

static void *get_current_thread_id(void)
{
    /* xxx This function is a hack on two fronts:

       - It assumes that pthread_self() is async-signal-safe.  This
         should be true on Linux.  I hope it is also true elsewhere.

       - It abuses pthread_self() by assuming it just returns an
         integer.  According to comments in CPython's source code, the
         platforms where it is not the case are rare nowadays.

       An alternative would be to try to look if the information is
       available in the ucontext_t in the caller.
    */
    return (void *)pthread_self();
}


/* *************************************************************
 * the signal handler
 * *************************************************************
 */

static void sigprof_handler(int sig_nr, siginfo_t* info, void *ucontext)
{
    long val = __sync_fetch_and_add(&signal_handler_value, 2L);

    if ((val & 1) == 0) {
        int saved_errno = errno;
        int fd = profile_file;
        assert(fd >= 0);

        struct profbuf_s *p = reserve_buffer(fd);
        if (p == NULL) {
            /* ignore this signal: there are no free buffers right now */
        }
        else {
            int depth;
            struct prof_stacktrace_s *st = (struct prof_stacktrace_s *)p->data;
            st->marker = MARKER_STACKTRACE;
            st->count = 1;
            st->stack[0] = GetPC((ucontext_t*)ucontext);
            depth = get_stack_trace(st->stack+1, MAX_STACK_DEPTH-2, ucontext);
            depth++;  // To account for pc value in stack[0];
            st->depth = depth;
            st->stack[depth++] = get_current_thread_id();
            p->data_offset = offsetof(struct prof_stacktrace_s, marker);
            p->data_size = (depth * sizeof(void *) +
                            sizeof(struct prof_stacktrace_s) -
                            offsetof(struct prof_stacktrace_s, marker));
            commit_buffer(fd, p);
        }

        errno = saved_errno;
    }

    __sync_sub_and_fetch(&signal_handler_value, 2L);
}


/* *************************************************************
 * the setup and teardown functions
 * *************************************************************
 */

static int install_sigprof_handler(void)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = sigprof_handler;
    sa.sa_flags = SA_RESTART | SA_SIGINFO;
    if (sigemptyset(&sa.sa_mask) == -1 ||
        sigaction(SIGPROF, &sa, NULL) == -1)
        return -1;
    return 0;
}

static int remove_sigprof_handler(void)
{
    if (signal(SIGPROF, SIG_DFL) == SIG_ERR)
        return -1;
    return 0;
}

static int install_sigprof_timer(void)
{
    static struct itimerval timer;
    timer.it_interval.tv_sec = 0;
    timer.it_interval.tv_usec = profile_interval_usec;
    timer.it_value = timer.it_interval;
    if (setitimer(ITIMER_PROF, &timer, NULL) != 0)
        return -1;
    return 0;
}

static int remove_sigprof_timer(void) {
    static struct itimerval timer;
    timer.it_interval.tv_sec = 0;
    timer.it_interval.tv_usec = 0;
    timer.it_value.tv_sec = 0;
    timer.it_value.tv_usec = 0;
    if (setitimer(ITIMER_PROF, &timer, NULL) != 0)
        return -1;
    return 0;
}

static void atfork_disable_timer(void) {
    if (profile_interval_usec > 0) {
        remove_sigprof_timer();
    }
}

static void atfork_enable_timer(void) {
    if (profile_interval_usec > 0) {
        install_sigprof_timer();
    }
}

static int install_pthread_atfork_hooks(void) {
    /* this is needed to prevent the problems described there:
         - http://code.google.com/p/gperftools/issues/detail?id=278
         - http://lists.debian.org/debian-glibc/2010/03/msg00161.html

        TL;DR: if the RSS of the process is large enough, the clone() syscall
        will be interrupted by the SIGPROF before it can complete, then
        retried, interrupted again and so on, in an endless loop.  The
        solution is to disable the timer around the fork, and re-enable it
        only inside the parent.
    */
    if (atfork_hook_installed)
        return 0;
    int ret = pthread_atfork(atfork_disable_timer, atfork_enable_timer, NULL);
    if (ret != 0)
        return -1;
    atfork_hook_installed = 1;
    return 0;
}

RPY_EXTERN
int vmprof_enable(void)
{
    assert(profile_file >= 0);
    assert(prepare_interval_usec > 0);
    profile_interval_usec = prepare_interval_usec;

    if (install_pthread_atfork_hooks() == -1)
        goto error;
    if (install_sigprof_handler() == -1)
        goto error;
    if (install_sigprof_timer() == -1)
        goto error;
    vmprof_ignore_signals(0);
    return 0;

 error:
    profile_file = -1;
    profile_interval_usec = 0;
    return -1;
}

static int _write_all(const void *buf, size_t bufsize)
{
    while (bufsize > 0) {
        ssize_t count = write(profile_file, buf, bufsize);
        if (count <= 0)
            return -1;   /* failed */
        buf += count;
        bufsize -= count;
    }
    return 0;
}

static int opened_profile(char *interp_name)
{
    struct {
        long hdr[5];
        char interp_name[259];
    } header;

    size_t namelen = strnlen(interp_name, 255);
    current_codes = NULL;

    header.hdr[0] = 0;
    header.hdr[1] = 3;
    header.hdr[2] = 0;
    header.hdr[3] = prepare_interval_usec;
    header.hdr[4] = 0;
    header.interp_name[0] = MARKER_HEADER;
    header.interp_name[1] = '\x00';
    header.interp_name[2] = VERSION_THREAD_ID;
    header.interp_name[3] = namelen;
    memcpy(&header.interp_name[4], interp_name, namelen);
    return _write_all(&header, 5 * sizeof(long) + 4 + namelen);
}

static int close_profile(void)
{
    char buf[4096];
    ssize_t size;
    unsigned char marker = MARKER_TRAILER;

    if (_write_all(&marker, 1) < 0)
        return -1;

#ifdef __linux__
    // copy /proc/self/maps to the end of the profile file
    int srcfd = open("/proc/self/maps", O_RDONLY);
    if (srcfd < 0)
        return -1;

    while ((size = read(srcfd, buf, sizeof buf)) > 0) {
        if (_write_all(buf, size) < 0) {
            close(srcfd);
            return -1;
        }
    }
    close(srcfd);
#else
    // freebsd and mac
#if defined(__APPLE__)
	sprintf(buf, "vmmap %d", getpid());
#else
    sprintf(buf, "procstat -v %d", getpid());
#endif
    FILE *srcf = popen(buf, "r");
    if (!srcf)
        return -1;

    while ((size = fread(buf, 1, sizeof buf, srcf))) {
        if (_write_all(buf, size) < 0) {
            pclose(srcf);
            return -1;
        }
    }
    pclose(srcf);
#endif

    /* don't close() the file descriptor from here */
    profile_file = -1;
    return 0;
}

RPY_EXTERN
int vmprof_disable(void)
{
    vmprof_ignore_signals(1);
    profile_interval_usec = 0;

    if (remove_sigprof_timer() == -1)
        return -1;
    if (remove_sigprof_handler() == -1)
        return -1;
    flush_codes();
    if (shutdown_concurrent_bufs(profile_file) < 0)
        return -1;
    return close_profile();
}

RPY_EXTERN
int vmprof_register_virtual_function(char *code_name, long code_uid,
                                     int auto_retry)
{
    long namelen = strnlen(code_name, 1023);
    long blocklen = 1 + 2 * sizeof(long) + namelen;
    struct profbuf_s *p;
    char *t;

 retry:
    p = current_codes;
    if (p != NULL) {
        if (__sync_bool_compare_and_swap(&current_codes, p, NULL)) {
            /* grabbed 'current_codes': we will append the current block
               to it if it contains enough room */
            size_t freesize = SINGLE_BUF_SIZE - p->data_size;
            if (freesize < blocklen) {
                /* full: flush it */
                commit_buffer(profile_file, p);
                p = NULL;
            }
        }
        else {
            /* compare-and-swap failed, don't try again */
            p = NULL;
        }
    }

    if (p == NULL) {
        p = reserve_buffer(profile_file);
        if (p == NULL) {
            /* can't get a free block; should almost never be the
               case.  Spin loop if allowed, or return a failure code
               if not (e.g. we're in a signal handler) */
            if (auto_retry > 0) {
                auto_retry--;
                usleep(1);
                goto retry;
            }
            return -1;
        }
    }

    t = p->data + p->data_size;
    p->data_size += blocklen;
    assert(p->data_size <= SINGLE_BUF_SIZE);
    *t++ = MARKER_VIRTUAL_IP;
    memcpy(t, &code_uid, sizeof(long)); t += sizeof(long);
    memcpy(t, &namelen, sizeof(long)); t += sizeof(long);
    memcpy(t, code_name, namelen);

    /* try to reattach 'p' to 'current_codes' */
    if (!__sync_bool_compare_and_swap(&current_codes, NULL, p)) {
        /* failed, flush it */
        commit_buffer(profile_file, p);
    }
    return 0;
}

static void flush_codes(void)
{
    struct profbuf_s *p = current_codes;
    if (p != NULL) {
        current_codes = NULL;
        commit_buffer(profile_file, p);
    }
}
