#include "skiplist.c"

volatile int pypy_codemap_currently_invalid = 0;

void pypy_codemap_invalid_set(int value)
{
    if (value)
        __sync_lock_test_and_set(&pypy_codemap_currently_invalid, 1);
    else
        __sync_lock_release(&pypy_codemap_currently_invalid);
}


/************************************************************/
/***  codemap storage                                     ***/
/************************************************************/

typedef struct {
    long machine_code_size;
    long *bytecode_info;
    long bytecode_info_size;
} codemap_data_t;

static skipnode_t jit_codemap_head;

/*** interface used from codemap.py ***/

long pypy_jit_codemap_add(uintptr_t addr, long machine_code_size,
                          long *bytecode_info, long bytecode_info_size)
{
    skipnode_t *new = skiplist_malloc(sizeof(codemap_data_t));
    codemap_data_t *data;
    if (new == NULL)
        return -1;   /* too bad */

    new->key = addr;
    data = (codemap_data_t *)new->data;
    data->machine_code_size = machine_code_size;
    data->bytecode_info = bytecode_info;
    data->bytecode_info_size = bytecode_info_size;

    pypy_codemap_invalid_set(1);
    skiplist_insert(&jit_codemap_head, new);
    pypy_codemap_invalid_set(0);
    return 0;
}

void pypy_jit_codemap_del(uintptr_t addr)
{
    skiplist_remove(&jit_codemap_head, addr);
}

/*** interface used from pypy/module/_vmprof ***/

void *pypy_find_codemap_at_addr(long addr)
{
    skiplist_t *codemap = skiplist_search(&jit_codemap_head, addr);
    codemap_data_t *data;
    uintptr_t rel_addr;

    if (codemap->key == NULL)
        return NULL;

    rel_addr = (uintptr_t)addr - codemap->key;
    data = (codemap_data_t *)codemap->data;
    if (rel_addr >= data->machine_code_size)
        return NULL;

    return (void *)codemap;
}

long pypy_yield_codemap_at_addr(void *codemap_raw, long addr,
                                long *current_pos_addr)
{
    // will return consecutive unique_ids from codemap, starting from position
    // `pos` until addr
    skiplist_t *codemap = (skiplist_t *)codemap_raw;
    long current_pos = *current_pos_addr;
    long rel_addr = addr - codemap->key;
    long next_start, next_stop;
    codemap_data_t *data = (codemap_data_t *)codemap->data;

    while (1) {
        if (current_pos >= data->bytecode_info_size)
            return 0;
        next_start = data->bytecode_info[current_pos + 1];
        if (next_start > rel_addr)
            return 0;
        next_stop = data->bytecode_info[current_pos + 2];
        if (next_stop > rel_addr) {
            *current_pos_addr = current_pos + 4;
            return data->bytecode_info[current_pos];
        }
        // we need to skip potentially more than one
        current_pos = data->bytecode_info[current_pos + 3];
    }
}

/************************************************************/



long pypy_jit_stack_depth_at_loc(long loc)
{
    long pos;
    pos = bisect_right(pypy_cs_g.jit_addr_map, loc,
                       pypy_cs_g.jit_addr_map_used);
    if (pos == 0)
        return -1;
    return pypy_cs_g.jit_frame_depth_map[pos - 1];
}

long pypy_find_codemap_at_addr(long addr)
{
    return bisect_right_addr(pypy_cs_g.jit_codemap, addr,
                             pypy_cs_g.jit_codemap_used) - 1;
}

long pypy_jit_start_addr(void)
{
    return pypy_cs_g.jit_addr_map[0];
}

long pypy_jit_end_addr(void)
{
    return pypy_cs_g.jit_addr_map[pypy_cs_g.jit_addr_map_used - 1];
}


pypy_codemap_storage *pypy_get_codemap_storage(void)
{
    return &pypy_cs_g;
}
