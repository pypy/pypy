
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

static long g_co_filename_ofs;
static long g_co_name_ofs;
static long g_co_firstlineno_ofs;
static long g_co_lnotab_ofs;

static char *_RPyString_AsString_Real(RPyString *obj)
{
    stm_char *src = _RPyString_AsString(obj);
    return STM_SEGMENT->segment_base + (uintptr_t)src;
}

static void _stm_expand_marker_for_pypy(uintptr_t odd_number,
                                        object_t *following_object,
                                        char *outputbuf, size_t outputbufsize)
{
    RPyString *co_filename =
        *(RPyString **)(((char *)following_object) + g_co_filename_ofs);
    RPyString *co_name =
        *(RPyString **)(((char *)following_object) + g_co_name_ofs);
    long co_firstlineno =
        *(long *)(((char *)following_object) + g_co_firstlineno_ofs);
    RPyString *co_lnotab =
        *(RPyString **)(((char *)following_object) + g_co_lnotab_ofs);

    char *ntrunc = "", *fntrunc = "";

    long remaining = outputbufsize - 32;
    long nlen = RPyString_Size(co_name);
    char *name = _RPyString_AsString_Real(co_name);
    if (nlen > remaining / 2) {
        nlen = remaining / 2;
        ntrunc = "...";
    }
    remaining -= nlen;

    long fnlen = RPyString_Size(co_filename);
    char *fn = _RPyString_AsString_Real(co_filename);
    if (fnlen > remaining) {
        fn += (fnlen - remaining);
        fnlen = remaining;
        fntrunc = "...";
    }

    long tablen = RPyString_Size(co_lnotab);
    char *tab = _RPyString_AsString_Real(co_lnotab);
    uintptr_t next_instr = odd_number >> 1;
    long line = co_firstlineno;
    uintptr_t i, addr = 0;
    for (i = 0; i < tablen; i += 2) {
        addr += ((unsigned char *)tab)[i];
        if (addr > next_instr)
            break;
        line += ((unsigned char *)tab)[i + 1];
    }

    snprintf(outputbuf, outputbufsize, "File \"%s%.*s\", line %ld, in %.*s%s",
             fntrunc, (int)fnlen, fn, line, (int)nlen, name, ntrunc);
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
}
