/* VMPROF
 *
 * statistical sampling profiler specifically designed to profile programs
 * which run on a Virtual Machine and/or bytecode interpreter, such as Python,
 * etc.
 *
 * The logic to dump the C stack traces is partly stolen from the code in gperftools.
 * The file "getpc.h" has been entirely copied from gperftools.
 *
 * Tested only on gcc, linux, x86_64.
 *
 * Copyright (C) 2014-2015
 *   Antonio Cuni - anto.cuni@gmail.com
 *   Maciej Fijalkowski - fijall@gmail.com
 *
 */


#include "getpc.h"      // should be first to get the _GNU_SOURCE dfn
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <assert.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/types.h>
#include <errno.h>
#include <pthread.h>
#include <dlfcn.h>

//#define UNW_LOCAL_ONLY
//#include <libunwind.h>

#include "vmprof.h"

#define _unused(x) ((void)x)

#define MAX_FUNC_NAME 128
#define MAX_STACK_DEPTH 1024
#define BUFFER_SIZE 8192


static int profile_file = 0;
static char profile_write_buffer[BUFFER_SIZE];
static int profile_buffer_position = 0;
void* vmprof_mainloop_func;
char* vmprof_error = NULL;
static ptrdiff_t mainloop_sp_offset;
static vmprof_get_virtual_ip_t mainloop_get_virtual_ip;
static long last_period_usec = 0;
static int atfork_hook_installed = 0;


/* *************************************************************
 * functions to write a profile file compatible with gperftools
 * *************************************************************
 */

#define MARKER_STACKTRACE '\x01'
#define MARKER_VIRTUAL_IP '\x02'
#define MARKER_TRAILER '\x03'

int (*unw_get_reg)(unw_cursor_t*, int, unw_word_t*) = NULL;
int (*unw_step)(unw_cursor_t*) = NULL;
int (*unw_init_local)(unw_cursor_t *, unw_context_t *) = NULL;
int (*unw_get_proc_info)(unw_cursor_t *, unw_proc_info_t *) = NULL;

static void prof_word(long x) {
	((long*)(profile_write_buffer + profile_buffer_position))[0] = x;
	profile_buffer_position += sizeof(long);
}

static void prof_header(long period_usec) {
    // XXX never used here?
    prof_word(0);
    prof_word(3);
    prof_word(0);
    prof_word(period_usec);
    prof_word(0);
    write(profile_file, profile_write_buffer, profile_buffer_position);
    profile_buffer_position = 0;
}

static void prof_write_stacktrace(void** stack, int depth, int count) {
    int i;
	char marker = MARKER_STACKTRACE;

	profile_write_buffer[profile_buffer_position++] = MARKER_STACKTRACE;
    prof_word(count);
    prof_word(depth);
    for(i=0; i<depth; i++)
        prof_word((long)stack[i]);
    write(profile_file, profile_write_buffer, profile_buffer_position);
    profile_buffer_position = 0;
}


/* ******************************************************
 * libunwind workaround for process JIT frames correctly
 * ******************************************************
 */

#include "get_custom_offset.c"

typedef struct {
    void* _unused1;
    void* _unused2;
    void* sp;
    void* ip;
    void* _unused3[sizeof(unw_cursor_t)/sizeof(void*) - 4];
} vmprof_hacked_unw_cursor_t;

static int vmprof_unw_step(unw_cursor_t *cp, int first_run) {
	void* ip;
    void* sp;
    ptrdiff_t sp_offset;
    unw_get_reg (cp, UNW_REG_IP, (unw_word_t*)&ip);
    unw_get_reg (cp, UNW_REG_SP, (unw_word_t*)&sp);
	if (!first_run)
		// make sure we're pointing to the CALL and not to the first
		// instruction after. If the callee adjusts the stack for us
		// it's not safe to be at the instruction after
		ip -= 1;
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

// The original code here has a comment, "stolen from pprof",
// about a "__thread int recursive".  But general __thread
// variables are not really supposed to be accessed from a
// signal handler.  Moreover, we are using SIGPROF, which
// should not be recursively called on the same thread.
//static __thread int recursive;

int get_stack_trace(void** result, int max_depth, ucontext_t *ucontext) {
    void *ip;
    int n = 0;
    unw_cursor_t cursor;
    unw_context_t uc = *ucontext;
    //if (recursive) {
    //    return 0;
    //}
    if (!custom_sanity_check()) {
        return 0;
    }
    //++recursive;

    int ret = unw_init_local(&cursor, &uc);
    assert(ret >= 0);
    _unused(ret);
	int first_run = 1;

    while (n < max_depth) {
        if (unw_get_reg(&cursor, UNW_REG_IP, (unw_word_t *) &ip) < 0) {
            break;
        }

        unw_proc_info_t pip;
        unw_get_proc_info(&cursor, &pip);

        /* char funcname[4096]; */
        /* unw_word_t offset; */
        /* unw_get_proc_name(&cursor, funcname, 4096, &offset); */
        /* printf("%s+%#lx <%p>\n", funcname, offset, ip); */

        /* if n==0, it means that the signal handler interrupted us while we
           were in the trampoline, so we are not executing (yet) the real main
           loop function; just skip it */
        if (vmprof_mainloop_func && 
            (void*)pip.start_ip == (void*)vmprof_mainloop_func &&
            n > 0) {
          // found main loop stack frame
          void* sp;
          unw_get_reg(&cursor, UNW_REG_SP, (unw_word_t *) &sp);
          void *arg_addr = (char*)sp + mainloop_sp_offset;
          void **arg_ptr = (void**)arg_addr;
          // fprintf(stderr, "stacktrace mainloop: rsp %p   &f2 %p   offset %ld\n", 
          //         sp, arg_addr, mainloop_sp_offset);
		  if (mainloop_get_virtual_ip) {
			  ip = mainloop_get_virtual_ip(*arg_ptr);
		  } else {
			  ip = *arg_ptr;
		  }
        }

        result[n++] = ip;
		n = vmprof_write_header_for_jit_addr(result, n, ip, max_depth);
        if (vmprof_unw_step(&cursor, first_run) <= 0) {
            break;
        }
		first_run = 0;
    }
    //--recursive;
    return n;
}


static int __attribute__((noinline)) frame_forcer(int rv) {
    return rv;
}

static void sigprof_handler(int sig_nr, siginfo_t* info, void *ucontext) {
    void* stack[MAX_STACK_DEPTH];
    int saved_errno = errno;
    stack[0] = GetPC((ucontext_t*)ucontext);
    int depth = frame_forcer(get_stack_trace(stack+1, MAX_STACK_DEPTH-1, ucontext));
    depth++;  // To account for pc value in stack[0];
    prof_write_stacktrace(stack, depth, 1);
    errno = saved_errno;
}

/* *************************************************************
 * functions to enable/disable the profiler
 * *************************************************************
 */

static int open_profile(int fd, long period_usec, int write_header, char *s,
						int slen) {
	if ((fd = dup(fd)) == -1) {
		return -1;
	}
	profile_buffer_position = 0;
    profile_file = fd;
	if (write_header)
		prof_header(period_usec);
	if (s)
		write(profile_file, s, slen);
	return 0;
}

static int close_profile(void) {
	// XXX all of this can happily fail
    FILE* src;
    char buf[BUFSIZ];
    size_t size;
	int marker = MARKER_TRAILER;
	write(profile_file, &marker, 1);

    // copy /proc/PID/maps to the end of the profile file
    sprintf(buf, "/proc/%d/maps", getpid());
    src = fopen(buf, "r");    
    while ((size = fread(buf, 1, BUFSIZ, src))) {
        write(profile_file, buf, size);
    }
    fclose(src);
    close(profile_file);
	return 0;
}


static int install_sigprof_handler(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = sigprof_handler;
    sa.sa_flags = SA_RESTART | SA_SIGINFO;
    if (sigemptyset(&sa.sa_mask) == -1 ||
		sigaction(SIGPROF, &sa, NULL) == -1) {
		return -1;
	}
	return 0;
}

static int remove_sigprof_handler(void) {
    sighandler_t res = signal(SIGPROF, SIG_DFL);
	if (res == SIG_ERR) {
		return -1;
	}
	return 0;
};

static int install_sigprof_timer(long period_usec) {
    static struct itimerval timer;
    last_period_usec = period_usec;
    timer.it_interval.tv_sec = 0;
    timer.it_interval.tv_usec = period_usec;
    timer.it_value = timer.it_interval;
    if (setitimer(ITIMER_PROF, &timer, NULL) != 0) {
		return -1;
    }
	return 0;
}

static int remove_sigprof_timer(void) {
    static struct itimerval timer;
    last_period_usec = 0;
    timer.it_interval.tv_sec = 0;
    timer.it_interval.tv_usec = 0;
    timer.it_value.tv_sec = 0;
    timer.it_value.tv_usec = 0;
    if (setitimer(ITIMER_PROF, &timer, NULL) != 0) {
		return -1;
    }
	return 0;
}

static void atfork_disable_timer(void) {
    remove_sigprof_timer();
}

static void atfork_enable_timer(void) {
    install_sigprof_timer(last_period_usec);
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

/* *************************************************************
 * public API
 * *************************************************************
 */

int vmprof_set_mainloop(void* func, ptrdiff_t sp_offset, 
                         vmprof_get_virtual_ip_t get_virtual_ip) {
    void *libhandle;

    mainloop_sp_offset = sp_offset;
    mainloop_get_virtual_ip = get_virtual_ip;
    vmprof_mainloop_func = func;
    if (!unw_get_reg) {
        if (!(libhandle = dlopen("libunwind.so", RTLD_LAZY | RTLD_LOCAL))) {
            vmprof_error = dlerror();
            return -1;
        }
        if (!(unw_get_reg = dlsym(libhandle, "_ULx86_64_get_reg"))) {
            vmprof_error = dlerror();
            return -1;
        }
        if (!(unw_get_proc_info = dlsym(libhandle, "_ULx86_64_get_proc_info"))){
            vmprof_error = dlerror();
            return -1;
        }
        if (!(unw_init_local = dlsym(libhandle, "_ULx86_64_init_local"))) {
            vmprof_error = dlerror();
            return -1;
        }
        if (!(unw_step = dlsym(libhandle, "_ULx86_64_step"))) {
            vmprof_error = dlerror();
            return -1;
        }
    }
    return 0;
}

char* vmprof_get_error()
{
    char* res;
    res = vmprof_error;
    vmprof_error = NULL;
    return res;
}

int vmprof_enable(int fd, long period_usec, int write_header, char *s,
				  int slen)
{
    assert(period_usec > 0);
    if (open_profile(fd, period_usec, write_header, s, slen) == -1) {
		return -1;
	}
    if (install_sigprof_handler() == -1) {
		return -1;
	}
    if (install_sigprof_timer(period_usec) == -1) {
		return -1;
	}
    if (install_pthread_atfork_hooks() == -1) {
        return -1;
    }
	return 0;
}

int vmprof_disable(void) {
    if (remove_sigprof_timer() == -1) {
		return -1;
	}
    if (remove_sigprof_handler() == -1) {
		return -1;
	}
    if (close_profile() == -1) {
		return -1;
	}
	return 0;
}

void vmprof_register_virtual_function(const char* name, void* start, void* end) {
	// XXX unused by pypy
    // for now *end is simply ignored
	char buf[1024];
	int lgt = strlen(name) + 2 * sizeof(long) + 1;

	if (lgt > 1024) {
		lgt = 1024;
	}
	buf[0] = MARKER_VIRTUAL_IP;
	((void **)(((void*)buf) + 1))[0] = start;
	((long *)(((void*)buf) + 1 + sizeof(long)))[0] = lgt - 2 * sizeof(long) - 1;
	strncpy(buf + 2 * sizeof(long) + 1, name, 1024 - 2 * sizeof(long) - 1);
	write(profile_file, buf, lgt);
}
