#include "vmp_stack.h"

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <stddef.h>
#include <assert.h>

#include "vmprof.h"
#include "compat.h"

#ifdef VMP_SUPPORTS_NATIVE_PROFILING
#include "unwind/vmprof_unwind.h"

typedef mcontext_t unw_context_t;

// functions copied from libunwind using dlopen

static int (*unw_get_reg)(unw_cursor_t*, int, unw_word_t*) = NULL;
static int (*unw_step)(unw_cursor_t*) = NULL;
static int (*unw_init_local)(unw_cursor_t *, unw_context_t *) = NULL;
static int (*unw_get_proc_info)(unw_cursor_t *, unw_proc_info_t *) = NULL;
static int (*unw_get_proc_name)(unw_cursor_t *, char *, size_t, unw_word_t*) = NULL;
static int (*unw_is_signal_frame)(unw_cursor_t *) = NULL;
static int (*unw_getcontext)(unw_context_t *) = NULL;

#endif

#ifdef __APPLE__
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/message.h>
#include <mach/kern_return.h>
#include <mach/task_info.h>
#include <sys/types.h>
#include <unistd.h>
#include <dlfcn.h>
#elif defined(__unix__)
#include <dlfcn.h>
#endif

#ifdef PY_TEST
// for testing only!
PY_EVAL_RETURN_T * vmprof_eval(PY_STACK_FRAME_T *f, int throwflag) { return NULL; }
#endif

static int vmp_native_traces_enabled = 0;
static intptr_t *vmp_ranges = NULL;
static ssize_t vmp_range_count = 0;
static int _vmp_profiles_lines = 0;

void vmp_profile_lines(int lines) {
    _vmp_profiles_lines = lines;
}
int vmp_profiles_python_lines(void) {
    return _vmp_profiles_lines;
}

static PY_STACK_FRAME_T * _write_python_stack_entry(PY_STACK_FRAME_T * frame, void ** result, int * depth, int max_depth)
{
    int len;
    int addr;
    int j;
    uint64_t line;
    char *lnotab;

#ifndef RPYTHON_VMPROF // pypy does not support line profiling
    if (vmp_profiles_python_lines()) {
        // In the line profiling mode we save a line number for every frame.
        // Actual line number isn't stored in the frame directly (f_lineno
        // points to the beginning of the frame), so we need to compute it
        // from f_lasti and f_code->co_lnotab. Here is explained what co_lnotab
        // is:
        // https://svn.python.org/projects/python/trunk/Objects/lnotab_notes.txt

        // NOTE: the profiling overhead can be reduced by storing co_lnotab in the dump and
        // moving this computation to the reader instead of doing it here.
        lnotab = PyStr_AS_STRING(frame->f_code->co_lnotab);

        if (lnotab != NULL) {
            line = (uint64_t)frame->f_lineno;
            addr = 0;

            len = (int)PyStr_GET_SIZE(frame->f_code->co_lnotab);

            for (j = 0; j < len; j += 2) {
                addr += lnotab[j];
                if (addr > frame->f_lasti) {
                    break;
                }
                line += lnotab[j+1];
            }
            result[*depth] = (void*) line;
            *depth = *depth + 1;
        } else {
            result[*depth] = (void*) 0;
            *depth = *depth + 1;
        }
    }
    result[*depth] = (void*)CODE_ADDR_TO_UID(FRAME_CODE(frame));
    *depth = *depth + 1;
#else

    if (frame->kind == VMPROF_CODE_TAG) {
        int n = *depth;
        result[n++] = (void*)frame->kind;
        result[n++] = (void*)frame->value;
        *depth = n;
    }
#ifdef PYPY_JIT_CODEMAP
    else if (frame->kind == VMPROF_JITTED_TAG) {
        intptr_t pc = ((intptr_t*)(frame->value - sizeof(intptr_t)))[0];
        *depth = vmprof_write_header_for_jit_addr(result, *depth, pc, max_depth);
    }
#endif


#endif

    return FRAME_STEP(frame);
}

int vmp_walk_and_record_python_stack_only(PY_STACK_FRAME_T *frame, void ** result,
                                     int max_depth, int depth, intptr_t pc)
{
    while (depth < max_depth && frame) {
        frame = _write_python_stack_entry(frame, result, &depth, max_depth);
    }
    return depth;
}

#ifdef VMP_SUPPORTS_NATIVE_PROFILING
int _write_native_stack(void* addr, void ** result, int depth) {
#ifdef RPYTHON_VMPROF
    result[depth++] = (void*)VMPROF_NATIVE_TAG;
#else
    if (vmp_profiles_python_lines()) {
        // even if we do not log a python stack frame,
        // we must keep the profile readable
        result[depth++] = 0;
    }
#endif
    result[depth++] = addr;
    return depth;
}
#endif

int vmp_walk_and_record_stack(PY_STACK_FRAME_T *frame, void ** result,
                              int max_depth, int signal, intptr_t pc) {

    // called in signal handler
#ifdef VMP_SUPPORTS_NATIVE_PROFILING
    intptr_t func_addr;
    unw_cursor_t cursor;
    unw_context_t uc;
    unw_proc_info_t pip;

    if (!vmp_native_enabled()) {
        return vmp_walk_and_record_python_stack_only(frame, result, max_depth, 0, pc);
    }

    unw_getcontext(&uc);
    int ret = unw_init_local(&cursor, &uc);
    if (ret < 0) {
        // could not initialize lib unwind cursor and context
        return 0;
    }

    if (signal < 0) {
        while (signal < 0) {
            int err = unw_step(&cursor);
            if (err <= 0) {
                return 0;
            }
            signal++;
        }
    } else {
#ifdef VMPROF_LINUX
        while (signal) {
            int is_signal_frame = unw_is_signal_frame(&cursor);
            if (is_signal_frame) {
                unw_step(&cursor); // step once more discard signal frame
                break;
            }
            int err = unw_step(&cursor);
            if (err <= 0) {
                return 0;
            }
        }
#else
        // who would have guessed that unw_is_signal_frame does not work on mac os x
        if (signal) {
            unw_step(&cursor); // vmp_walk_and_record_stack
            // get_stack_trace is inlined
            unw_step(&cursor); // _vmprof_sample_stack
            unw_step(&cursor); // sigprof_handler
            unw_step(&cursor); // _sigtramp
        }
#endif
    }

    int depth = 0;
    PY_STACK_FRAME_T * top_most_frame = frame;
    while (depth < max_depth) {
        unw_get_proc_info(&cursor, &pip);

        func_addr = pip.start_ip;

        //{
        //    char name[64];
        //    unw_word_t x;
        //    unw_get_proc_name(&cursor, name, 64, &x);
        //    printf("  %s %p\n", name, func_addr);
        //}

        //if (func_addr == 0) {
        //    unw_word_t rip = 0;
        //    if (unw_get_reg(&cursor, UNW_REG_IP, &rip) < 0) {
        //        printf("failed failed failed\n");
        //    }
        //    func_addr = rip;
        //    printf("func_addr is 0, now %p\n", rip);
        //}

#ifdef PYPY_JIT_CODEMAP
        long start_addr = 0;
        unw_word_t rip = 0;
        if (unw_get_reg(&cursor, UNW_REG_IP, &rip) < 0) {
            return 0;
        }
#endif

        if (IS_VMPROF_EVAL((void*)pip.start_ip)) {
            // yes we found one stack entry of the python frames!
            return vmp_walk_and_record_python_stack_only(frame, result, max_depth, depth, pc);
#ifdef PYPY_JIT_CODEMAP
        } else if (pypy_find_codemap_at_addr(rip, &start_addr) != NULL) {
            depth = vmprof_write_header_for_jit_addr(result, depth, pc, max_depth);
            return vmp_walk_and_record_python_stack_only(frame, result, max_depth, depth, pc);
#endif
        } else {
            // mark native routines with the first bit set,
            // this is possible because compiler align to 8 bytes.
            //
            if (func_addr != 0x0) {
                depth = _write_native_stack((void*)(func_addr | 0x1), result, depth);
            }
        }

        int err = unw_step(&cursor);
        if (err == 0) {
            break;
        } else if (err < 0) {
            return 0; // this sample is broken, cannot walk it fully
        }
    }

    return 0; // kill this sample, no python level was found
#else
    return vmp_walk_and_record_python_stack_only(frame, result, max_depth, 0, pc);
#endif
}

int vmp_native_enabled(void) {
#ifdef VMP_SUPPORTS_NATIVE_PROFILING
    return vmp_native_traces_enabled;
#else
    return 0;
#endif
}

#ifdef VMP_SUPPORTS_NATIVE_PROFILING
int _ignore_symbols_from_path(const char * name) {
    // which symbols should not be considered while walking
    // the native stack?
#ifdef RPYTHON_VMPROF
    if (strstr(name, "libpypy-c.so") != NULL
        || strstr(name, "pypy-c") != NULL) {
        return 1;
    }
#else
    // cpython
    if (strstr(name, "python") != NULL &&
#  ifdef __unix__
        strstr(name, ".so\n") == NULL
#  elif defined(__APPLE__)
        strstr(name, ".so") == NULL
#  endif
       ) {
        return 1;
    }
#endif
    return 0;
}

int _reset_vmp_ranges(void) {
    // initially 10 (start, stop) entries!
    int max_count = 10;
    vmp_range_count = 0;
    if (vmp_ranges != NULL) { free(vmp_ranges); }
    vmp_ranges = malloc(max_count * sizeof(intptr_t));
    return max_count;
}


int _resize_ranges(intptr_t ** cursor, int max_count) {
    ptrdiff_t diff = (*cursor - vmp_ranges);
    if (diff + 2 > max_count) {
        max_count *= 2;
        vmp_ranges = realloc(vmp_ranges, max_count*sizeof(intptr_t));
        *cursor = vmp_ranges + diff;
    }
    return max_count;
}

intptr_t * _add_to_range(intptr_t * cursor, intptr_t start, intptr_t end) {
    if (cursor[0] == start) {
        // the last range is extended, this reduces the entry count
        // which makes the querying faster
        cursor[0] = end;
    } else {
        if (cursor != vmp_ranges) {
            // not pointing to the first entry
            cursor++;
        }
        cursor[0] = start;
        cursor[1] = end;
        vmp_range_count += 2;
        cursor++;
    }
    return cursor;
}

#ifdef __unix__
int vmp_read_vmaps(const char * fname) {

    FILE * fd = fopen(fname, "rb");
    if (fd == NULL) {
        return 0;
    }
    char * saveptr;
    char * line = NULL;
    char * he = NULL;
    char * name;
    char *start_hex = NULL, *end_hex = NULL;
    size_t n = 0;
    ssize_t size;
    intptr_t start, end;

    // assumptions to be verified:
    // 1) /proc/self/maps is ordered ascending by start address
    // 2) libraries that contain the name 'python' are considered
    //    candidates in the mapping to be ignored
    // 3) libraries containing site-packages are not considered
    //    candidates

    int max_count = _reset_vmp_ranges();
    intptr_t * cursor = vmp_ranges;
    cursor[0] = -1;
    while ((size = getline(&line, &n, fd)) >= 0) {
        assert(line != NULL);
        start_hex = strtok_r(line, "-", &saveptr);
        if (start_hex == NULL) { continue; }
        start = strtoll(start_hex, &he, 16);
        end_hex = strtok_r(NULL, " ", &saveptr);
        if (end_hex == NULL) { continue; }
        end = strtoll(end_hex, &he, 16);
        // skip over flags, ...
        strtok_r(NULL, " ", &saveptr);
        strtok_r(NULL, " ", &saveptr);
        strtok_r(NULL, " ", &saveptr);
        strtok_r(NULL, " ", &saveptr);

        name = saveptr;
        if (_ignore_symbols_from_path(name)) {
            max_count = _resize_ranges(&cursor, max_count);
            cursor = _add_to_range(cursor, start, end);
        }
        free(line);
        line = NULL;
        n = 0;
    }

    fclose(fd);
    return 1;
}
#endif

#ifdef __APPLE__
int vmp_read_vmaps(const char * fname) {
    kern_return_t kr;
    task_t task;
    mach_vm_address_t addr;
    mach_vm_size_t vmsize;
    vm_region_top_info_data_t topinfo;
    mach_msg_type_number_t count;
    memory_object_name_t obj;
    int ret = 0;
    pid_t pid;

    pid = getpid();
    kr = task_for_pid(mach_task_self(), pid, &task);
    if (kr != KERN_SUCCESS) {
        goto teardown;
    }

    addr = 0;
    int max_count = _reset_vmp_ranges();
    intptr_t * cursor = vmp_ranges;
    cursor[0] = -1;

    do {
        // extract the top info using vm_region
        count = VM_REGION_TOP_INFO_COUNT;
        vmsize = 0;
        kr = mach_vm_region(task, &addr, &vmsize, VM_REGION_TOP_INFO,
                          (vm_region_info_t)&topinfo, &count, &obj);
        if (kr == KERN_SUCCESS) {
            vm_address_t start = addr, end = addr + vmsize;
            // dladdr now gives the path of the shared object
            Dl_info info;
            if (dladdr((const void*)start, &info) == 0) {
                // could not find image containing start
                addr += vmsize;
                continue;
            }
            if (_ignore_symbols_from_path(info.dli_fname)) {
                // realloc if the chunk is to small
                max_count = _resize_ranges(&cursor, max_count);
                cursor = _add_to_range(cursor, start, end);
            }
            addr = addr + vmsize;
        } else if (kr != KERN_INVALID_ADDRESS) {
            goto teardown;
        }
    } while (kr == KERN_SUCCESS);

    ret = 1;

teardown:
    if (task != MACH_PORT_NULL) {
        mach_port_deallocate(mach_task_self(), task);
    }
    return ret;
}
#endif

static const char * vmprof_error = NULL;
static void * libhandle = NULL;


#ifdef VMPROF_LINUX
#define LIBUNWIND "libunwind.so"
#ifdef __i386__
#define PREFIX "x86"
#elif __x86_64__
#define PREFIX "x86_64"
#endif
#define U_PREFIX "_U"
#define UL_PREFIX "_UL"
#else
#define LIBUNWIND "/usr/lib/system/libunwind.dylib"
#define PREFIX "unw"
#define U_PREFIX ""
#define UL_PREFIX ""
#endif

int vmp_native_enable(void) {
    vmp_native_traces_enabled = 1;

    if (!unw_get_reg) {
        if (!(libhandle = dlopen(LIBUNWIND, RTLD_LAZY | RTLD_LOCAL))) {
            goto bail_out;
        }
        if (!(unw_get_reg = dlsym(libhandle, UL_PREFIX PREFIX "_get_reg"))) {
            goto bail_out;
        }
        if (!(unw_get_proc_info = dlsym(libhandle, UL_PREFIX PREFIX "_get_proc_info"))){
            goto bail_out;
        }
        if (!(unw_get_proc_name = dlsym(libhandle, UL_PREFIX PREFIX "_get_proc_name"))){
            goto bail_out;
        }
        if (!(unw_init_local = dlsym(libhandle, UL_PREFIX PREFIX "_init_local"))) {
            goto bail_out;
        }
        if (!(unw_step = dlsym(libhandle, UL_PREFIX PREFIX "_step"))) {
            goto bail_out;
        }
        if (!(unw_is_signal_frame = dlsym(libhandle, UL_PREFIX PREFIX "_is_signal_frame"))) {
            goto bail_out;
        }
        if (!(unw_getcontext = dlsym(libhandle, U_PREFIX PREFIX "_getcontext"))) {
            goto bail_out;
        }
    }

#if defined(__unix__)
    return vmp_read_vmaps("/proc/self/maps");
#elif defined(__APPLE__)
    return vmp_read_vmaps(NULL);
#endif
bail_out:
    vmprof_error = dlerror();
    fprintf(stderr, "could not load libunwind at runtime. error: %s\n", vmprof_error);
    vmp_native_traces_enabled = 0;
    return 0;
}

void vmp_native_disable(void) {

    if (libhandle != NULL) {
        if (dlclose(libhandle)) {
            vmprof_error = dlerror();
            fprintf(stderr, "could not close libunwind at runtime. error: %s\n", vmprof_error);
        }
    }

    vmp_native_traces_enabled = 0;
    if (vmp_ranges != NULL) {
        free(vmp_ranges);
        vmp_ranges = NULL;
    }
    vmp_range_count = 0;
}

int vmp_ignore_ip(intptr_t ip) {
    if (vmp_range_count == 0) {
        return 0;
    }
    int i = vmp_binary_search_ranges(ip, vmp_ranges, vmp_range_count);
    if (i == -1) {
        return 0;
    }

    assert((i & 1) == 0 && "returned index MUST be even");

    intptr_t v = vmp_ranges[i];
    intptr_t v2 = vmp_ranges[i+1];
    return v <= ip && ip <= v2;
}

int vmp_binary_search_ranges(intptr_t ip, intptr_t * l, int count) {
    intptr_t * r = l + count;
    intptr_t * ol = l;
    intptr_t * or = r-1;
    while (1) {
        ptrdiff_t i = (r-l)/2;
        if (i == 0) {
            if (l == ol && *l > ip) {
                // at the start
                return -1;
            } else if (l == or && *l < ip) {
                // at the end
                return -1;
            } else {
                // we found the lower bound
                i = l - ol;
                if ((i & 1) == 1) {
                    return i-1;
                }
                return i;
            }
        }
        intptr_t * m = l + i;
        if (ip < *m) {
            r = m;
        } else {
            l = m;
        }
    }
    return -1;
}

int vmp_ignore_symbol_count(void) {
    return vmp_range_count;
}

intptr_t * vmp_ignore_symbols(void) {
    return vmp_ranges;
}

void vmp_set_ignore_symbols(intptr_t * symbols, int count) {
    vmp_ranges = symbols;
    vmp_range_count = count;
}
#endif
