
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
}

void pypy_stm_register_thread_local(void)
{
    stm_register_thread_local(&stm_thread_local);
    stm_thread_local.mem_clear_on_abort = (char *)&pypy_g_ExcData;
    stm_thread_local.mem_bytes_to_clear_on_abort = sizeof(pypy_g_ExcData);
}

void pypy_stm_unregister_thread_local(void)
{
    stm_flush_timing(&stm_thread_local, 1);  // XXX temporary
    stm_unregister_thread_local(&stm_thread_local);
}


/************************************************************/
/*** HACK: hard-coded logic to expand the marker into     ***/
/*** a string, suitable for running in PyPy               ***/

typedef struct pypy_rpy_string0 RPyStringSpace0;

static long g_co_filename_ofs;
static long g_co_name_ofs;
static long g_co_firstlineno_ofs;
static long g_co_lnotab_ofs;

static long _fetch_lngspace0(char *seg_base, object_t *base, long ofs)
{
    char *src = seg_base + (uintptr_t)base;
    return *(long *)(src + ofs);
}

static RPyStringSpace0 *_fetch_rpsspace0(char *seg_base, object_t *base,
                                         long ofs)
{
    char *src = seg_base + (uintptr_t)base;
    char *str = *(char **)(src + ofs);
    char *str0 = seg_base + (uintptr_t)str;
    return (RPyStringSpace0 *)str0;
}

static void _stm_expand_marker_for_pypy(
        char *segment_base, uintptr_t odd_number, object_t *o,
        char *outputbuf, size_t outputbufsize)
{
    long co_firstlineno;
    RPyStringSpace0 *co_filename;
    RPyStringSpace0 *co_name;
    RPyStringSpace0 *co_lnotab;
    char *ntrunc = "", *fntrunc = "";
    long fnlen = 1, nlen = 1, line = 0;
    char *fn = "?", *name = "?";

    if (o) {
        co_filename   =_fetch_rpsspace0(segment_base, o, g_co_filename_ofs);
        co_name       =_fetch_rpsspace0(segment_base, o, g_co_name_ofs);
        co_firstlineno=_fetch_lngspace0(segment_base, o, g_co_firstlineno_ofs);
        co_lnotab     =_fetch_rpsspace0(segment_base, o, g_co_lnotab_ofs);

        long remaining = outputbufsize - 32;
        nlen = RPyString_Size(co_name);
        name = _RPyString_AsString(co_name);
        if (nlen > remaining / 2) {
            nlen = remaining / 2;
            ntrunc = ">";
        }
        remaining -= nlen;

        fnlen = RPyString_Size(co_filename);
        fn = _RPyString_AsString(co_filename);
        if (fnlen > remaining) {
            fn += (fnlen - remaining);
            fnlen = remaining;
            fntrunc = "<";
        }

        long lnotablen = RPyString_Size(co_lnotab);
        char *lnotab = _RPyString_AsString(co_lnotab);
        uintptr_t next_instr = odd_number >> 1;
        line = co_firstlineno;
        uintptr_t i, addr = 0;
        for (i = 0; i < lnotablen; i += 2) {
            addr += ((unsigned char *)lnotab)[i];
            if (addr > next_instr)
                break;
            line += ((unsigned char *)lnotab)[i + 1];
        }
    }

    snprintf(outputbuf, outputbufsize, "File \"%s%.*s\", line %ld, in %.*s%s",
             fntrunc, (int)fnlen, fn, line, (int)nlen, name, ntrunc);
}

#define REPORT_MINIMUM_TIME   0.0001    /* 0.1 millisecond; xxx tweak */

static void _stm_cb_debug_print(const char *cause, double time,
                                const char *marker)
{
    if (time >= REPORT_MINIMUM_TIME) {
        PYPY_DEBUG_START("stm-report");
        fprintf(PYPY_DEBUG_FILE, "%s  %s\n%s    %.6fs: %s\n",
                pypy_debug_threadid, marker,
                pypy_debug_threadid, time, cause);
        PYPY_DEBUG_STOP("stm-report");
    }
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
    stmcb_expand_marker = _stm_expand_marker_for_pypy;

    PYPY_DEBUG_START("stm-report");
    if (PYPY_HAVE_DEBUG_PRINTS) {
        stmcb_debug_print = _stm_cb_debug_print;
    }
    PYPY_DEBUG_STOP("stm-report");
}
