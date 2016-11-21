#include <string.h>
#include <stdlib.h>

#ifdef RPYTHON_VMPROF
#include "src/threadlocal.h"
#endif


static void _stm_call_finalizer(object_t *obj)
{
    /* this function works for both regular and light finalizers */
    void *funcptr = pypy_stmcb_fetch_finalizer(((rpyobj_t *)obj)->tid);
    ((void(*)(object_t *))funcptr)(obj);
}

void pypy_stm_setup_prebuilt(void)
{
    object_t **pp = rpy_prebuilt;
    long *ph = rpy_prebuilt_hashes;
    int i = 0;
    int *wri = weakref_indices;
    for ( ; *pp; pp++, ph++, i++) {
        if (i == *wri) {
            *pp = stm_setup_prebuilt_weakref(*pp);
            wri++;
        }
        else {
            *pp = stm_setup_prebuilt(*pp);
        }
        stm_set_prebuilt_identityhash(*pp, *ph);
    }

    object_t ***cur = (object_t ***)
       pypy_g_rpython_memory_gctypelayout_GCData.gcd_inst_static_root_start;
    object_t ***end = (object_t ***)
       pypy_g_rpython_memory_gctypelayout_GCData.gcd_inst_static_root_nongcend;
    for ( ; cur != end; cur++) {
        **cur = stm_setup_prebuilt(**cur);
    }

    stmcb_finalizer = &_stm_call_finalizer;
    stmcb_destructor = &_stm_call_finalizer;
}

void pypy_stm_register_thread_local(void)
{
    stm_register_thread_local(&stm_thread_local);
    stm_thread_local.mem_clear_on_abort = (char *)&pypy_g_ExcData;
    stm_thread_local.mem_bytes_to_clear_on_abort = sizeof(pypy_g_ExcData);

#ifdef RPYTHON_VMPROF
    stm_thread_local.mem_reset_on_abort = (char *)&pypy_threadlocal.vmprof_tl_stack;
    stm_thread_local.mem_bytes_to_reset_on_abort = sizeof(pypy_threadlocal.vmprof_tl_stack);
    stm_thread_local.mem_stored_for_reset_on_abort = malloc(sizeof(pypy_threadlocal.vmprof_tl_stack));
#else
    stm_thread_local.mem_reset_on_abort = NULL;
#endif
}

void pypy_stm_unregister_thread_local(void)
{
    stm_unregister_thread_local(&stm_thread_local);
    stm_thread_local.shadowstack_base = NULL;
#ifdef RPYTHON_VMPROF
    free(stm_thread_local.mem_stored_for_reset_on_abort);
#endif
}


void pypy_stm_memclearinit(object_t *obj, size_t offset, size_t size)
{
    char *realobj = STM_SEGMENT->segment_base + (uintptr_t)obj;
    memset(realobj + offset, 0, size);
}

/************************************************************/
/*** HACK: hard-coded logic to expand the marker into     ***/
/*** a string, suitable for running in PyPy               ***/

#include <stdlib.h>    /* for getenv() */

static long g_co_filename_ofs;
static long g_co_name_ofs;
static long g_co_firstlineno_ofs;
static long g_co_lnotab_ofs;

static long _fetch_long(char *seg_base, long addr)
{
    return *(long *)(seg_base + addr);
}

static long _fetch_strlen(char *seg_base, long addr)
{
    long rpy_length_ofs = (long)&RPyString_Size((RPyString *)0);
    if (addr == 0)        /* xxx sanity-check */
        return 0;
    return _fetch_long(seg_base, addr + rpy_length_ofs);
}

static char *_fetch_stritems(char *seg_base, long addr)
{
    long rpy_items_ofs = (long)_RPyString_AsString((RPyString *)0);
    assert(addr != 0);
    return seg_base + addr + rpy_items_ofs;
}

static int _stm_expand_marker_for_pypy(char *segment_base,
                                       stm_loc_marker_t *marker,
                                       char *outputbuf, int outputbufsize)
{
    if (marker->object == NULL)
        return 0;

    long co_firstlineno;
    long co_filename;
    long co_name;
    long co_lnotab;
    char *ntrunc = "", *fntrunc = "";
    long fnlen = 1, nlen = 1, line = 0;
    char *fn = "?", *name = "?";

    long o = (long)marker->object;

    co_filename    = _fetch_long(segment_base, o + g_co_filename_ofs);
    co_name        = _fetch_long(segment_base, o + g_co_name_ofs);
    co_firstlineno = _fetch_long(segment_base, o + g_co_firstlineno_ofs);
    co_lnotab      = _fetch_long(segment_base, o + g_co_lnotab_ofs);

    long remaining = outputbufsize - 32;
    long ll = _fetch_strlen(segment_base, co_name);
    if (ll > 0) {
        nlen = ll;
        name = _fetch_stritems(segment_base, co_name);
        if (nlen > remaining / 2) {
            nlen = remaining / 2;
            ntrunc = ">";
        }
    }
    remaining -= nlen;

    ll = _fetch_strlen(segment_base, co_filename);
    if (ll > 0) {
        fnlen = ll;
        fn = _fetch_stritems(segment_base, co_filename);
        if (fnlen > remaining) {
            fn += (fnlen - remaining);
            fnlen = remaining;
            fntrunc = "<";
        }
    }

    uintptr_t next_instr = marker->odd_number >> 1;

    ll = _fetch_strlen(segment_base, co_lnotab);
    if (ll > 0) {
        long lnotablen = ll;
        unsigned char *lnotab = (unsigned char *)_fetch_stritems(segment_base,
                                                                 co_lnotab);
        line = co_firstlineno;
        uintptr_t ii, curaddr = 0;
        for (ii = 0; ii < lnotablen; ii += 2) {
            curaddr += lnotab[ii];
            if (curaddr > next_instr)
                break;
            line += lnotab[ii + 1];
        }
    }

    int result;
    result = snprintf(outputbuf, outputbufsize,
                      "File \"%s%.*s\", line %ld, in %.*s%s (#%ld)",
                      fntrunc, (int)fnlen, fn, line, (int)nlen,
                      name, ntrunc, next_instr);
    if (result >= outputbufsize)
        result = outputbufsize - 1;
    if (result < 0)
        result = 0;
    return result;
}

char *_pypy_stm_test_expand_marker(void)
{
    /* only for tests: XXX fishing */
    stm_loc_marker_t marker;
    char *segment_base = STM_SEGMENT->segment_base;

    struct stm_shadowentry_s *_ss = stm_thread_local.shadowstack - 2;
    while (!(((uintptr_t)(_ss->ss)) & 1)) {
        _ss--;
        assert(_ss >= stm_thread_local.shadowstack_base);
    }
    marker.odd_number = (uintptr_t)(_ss->ss);
    marker.object = (_ss + 1)->ss;

    static char buffer[80];
    int length;
    length = _stm_expand_marker_for_pypy(segment_base, &marker,buffer, 80);
    assert(length >= 0 && length < 80);
    buffer[length] = 0;
    return buffer;
}

void pypy_stm_setup_expand_marker(long co_filename_ofs,
                                  long co_name_ofs,
                                  long co_firstlineno_ofs,
                                  long co_lnotab_ofs)
{
    g_co_filename_ofs = co_filename_ofs;
    g_co_name_ofs = co_name_ofs;
    g_co_firstlineno_ofs = co_firstlineno_ofs;
    g_co_lnotab_ofs = co_lnotab_ofs;

    char *filename = getenv("PYPYSTM");
    if (filename && filename[0]) {
        /* if PYPYSTM is set to a string ending in '+', we enable the
           timing log also for forked subprocesses. */
        size_t n = strlen(filename);
        char filename_copy[n];
        int fork_mode = (n > 1 && filename[n - 1] == '+');
        if (fork_mode) {
            memcpy(filename_copy, filename, n - 1);
            filename_copy[n - 1] = 0;
            filename = filename_copy;
        }
        stm_set_timing_log(filename, fork_mode, &_stm_expand_marker_for_pypy);
    }
}
