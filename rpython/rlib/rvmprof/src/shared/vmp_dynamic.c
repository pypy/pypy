#include "vmp_dynamic.h"

#include <stdlib.h>
#include <string.h>
#include <assert.h>

static int g_dyn_entry_count = 0;
static int g_has_holes = -1;
static int g_dyn_entry_count_max = 0;
static unw_dyn_info_t ** g_dyn_entries = 0;

RPY_EXTERN
int vmp_dyn_teardown(void)
{
    int i;
    for (i = 0; i < g_dyn_entry_count; i++) {
        unw_dyn_info_t * u = g_dyn_entries[i];
        if (u != NULL) {
            free(u);
            g_dyn_entries[i] = NULL;
        }
    }
    if (g_dyn_entries != NULL) {
        free(g_dyn_entries);
    }
    g_dyn_entry_count = 0;
    g_dyn_entry_count_max = 0;
    g_has_holes = -1;
    return 0;
}

static void _vmp_dyn_resize(void) {
    if (g_dyn_entry_count_max == 0) {
        g_dyn_entry_count_max = 128;
        g_dyn_entries = (unw_dyn_info_t**)calloc(sizeof(unw_dyn_info_t*), 128);
    }

    if (g_dyn_entry_count + 1 >= g_dyn_entry_count_max) {
        g_dyn_entry_count_max *= 2;
        g_dyn_entries = (unw_dyn_info_t**)realloc(g_dyn_entries, sizeof(unw_dyn_info_t*) * g_dyn_entry_count_max);
        memset(g_dyn_entries + g_dyn_entry_count, 0,
               sizeof(unw_dyn_info_t*)*(g_dyn_entry_count_max - g_dyn_entry_count));
    }
}

static unw_dyn_info_t * _vmp_alloc_dyn_info(int * reference)
{
    unw_dyn_info_t * u;

    u = (unw_dyn_info_t*)malloc(sizeof(unw_dyn_info_t));

    int i = 0;
    int ref = -1;
    if (g_has_holes >= 0) {
        i = g_has_holes;
        while (i < g_dyn_entry_count) {
            if (g_dyn_entries[i] == NULL) {
                ref = i;
                g_has_holes += 1;
            }
        }
        if (i == g_dyn_entry_count) {
            _vmp_dyn_resize();
            ref = g_dyn_entry_count;
            g_dyn_entry_count++;
        }
    } else {
        _vmp_dyn_resize();
        ref = g_dyn_entry_count;
        g_dyn_entry_count++;
    }
    assert(ref != -1 && "ref position MUST be found");
    g_dyn_entries[ref] = u;
    *reference = ref;

    return u;
}

static void _vmp_free_dyn_info(unw_dyn_info_t * u)
{
    free(u);
}

RPY_EXTERN
int vmp_dyn_register_jit_page(intptr_t addr, intptr_t end_addr,
                              const char * name)
{
    char * name_cpy = NULL;
    int ref = -1;
    unw_dyn_info_t * u = _vmp_alloc_dyn_info(&ref);
    if (ref == -1) {
        return -1; // fail, could not alloc
    }
    u->start_ip = (unw_word_t)addr;
    u->end_ip = (unw_word_t)end_addr;
    u->format = UNW_INFO_FORMAT_DYNAMIC;
    if (name != NULL) {
        name_cpy = strdup(name);
    }
    unw_dyn_proc_info_t * ip = (unw_dyn_proc_info_t*)&(u->u);
    ip->name_ptr = (unw_word_t)name_cpy;
    ip->handler = 0;
    // the docs say, we cannot use this field. but looking at libunwind, it just copies
    // the value over when unw_get_proc_info is called. This should be fine to identify
    ip->flags = DYN_JIT_FLAG;
    ip->regions = NULL;

    _U_dyn_register(u);

    return ref;
}

RPY_EXTERN
int vmp_dyn_cancel(int ref) {
    unw_dyn_info_t * u;

    if (ref >= g_dyn_entry_count || ref < 0) {
        return 1;
    }
    
    u = g_dyn_entries[ref];
    if (u != NULL) {
        g_dyn_entries[ref] = NULL;
        if (g_has_holes > ref) {
            g_has_holes = ref;
        }

        _U_dyn_cancel(u);
    }

    _vmp_free_dyn_info(u);
    return 0;
}
