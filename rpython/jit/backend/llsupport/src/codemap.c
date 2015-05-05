#include "src/precommondefs.h"
#include <assert.h>

#ifndef HAS_SKIPLIST
# error "skiplist.c needs to be included before"
#endif

volatile int pypy_codemap_currently_invalid = 0;

void pypy_codemap_invalid_set(int value)
{
#ifndef _MSC_VER
    if (value)
        __sync_lock_test_and_set(&pypy_codemap_currently_invalid, 1);
    else
        __sync_lock_release(&pypy_codemap_currently_invalid);
#else
    _InterlockedExchange((long volatile *)&pypy_codemap_currently_invalid,
                        (long)value);
#endif
}


/************************************************************/
/***  codemap storage                                     ***/
/************************************************************/

typedef struct {
    unsigned int machine_code_size;
    unsigned int bytecode_info_size;
    long *bytecode_info;
} codemap_data_t;

static skipnode_t jit_codemap_head;

/*** interface used from codemap.py ***/

RPY_EXTERN
long pypy_jit_codemap_add(unsigned long addr, unsigned int machine_code_size,
                          long *bytecode_info, unsigned int bytecode_info_size)
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

RPY_EXTERN
long *pypy_jit_codemap_del(unsigned long addr, unsigned int size)
{
    unsigned long search_key = addr + size - 1;
    long *result;
    skipnode_t *node;

    /* There should be either zero or one codemap entry in the range.
       In theory it should take the complete range, but for alignment
       reasons the [addr, addr+size] range can be slightly bigger. */
    node = skiplist_search(&jit_codemap_head, search_key);
    if (node->key < addr)
        return NULL;

    pypy_codemap_invalid_set(1);
    skiplist_remove(&jit_codemap_head, node->key);
    pypy_codemap_invalid_set(0);

    /* there should be at most one */
    assert(skiplist_search(&jit_codemap_head, search_key)->key < addr);

    result = ((codemap_data_t *)node->data)->bytecode_info;
    free(node);
    return result;
}

RPY_EXTERN
unsigned long pypy_jit_codemap_firstkey(void)
{
    return skiplist_firstkey(&jit_codemap_head);
}

/*** interface used from pypy/module/_vmprof ***/

RPY_EXTERN
void *pypy_find_codemap_at_addr(long addr, long* start_addr)
{
    skipnode_t *codemap = skiplist_search(&jit_codemap_head, addr);
    codemap_data_t *data;
    unsigned long rel_addr;

    if (codemap == &jit_codemap_head) {
        if (start_addr)
            *start_addr = 0;
        return NULL;
    }

    rel_addr = (unsigned long)addr - codemap->key;
    data = (codemap_data_t *)codemap->data;
    if (rel_addr >= data->machine_code_size) {
        if (start_addr)
            *start_addr = 0;
        return NULL;
    }

    if (start_addr)
        *start_addr = (long)codemap->key;
    return (void *)codemap;
}

RPY_EXTERN
long pypy_yield_codemap_at_addr(void *codemap_raw, long addr,
                                long *current_pos_addr)
{
    // will return consecutive unique_ids from codemap, starting from position
    // `pos` until addr
    skipnode_t *codemap = (skipnode_t *)codemap_raw;
    long current_pos = *current_pos_addr;
    long rel_addr = addr - codemap->key;
    long next_start, next_stop;
    codemap_data_t *data = (codemap_data_t *)codemap->data;

    while (1) {
        if (current_pos >= data->bytecode_info_size)
            return -1;
        next_start = data->bytecode_info[current_pos + 1];
        if (next_start > rel_addr)
            return -1;
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
/***  depthmap storage                                    ***/
/************************************************************/

typedef struct {
    unsigned int block_size;
    unsigned int stack_depth;
} depthmap_data_t;

static skipnode_t jit_depthmap_head;

/*** interface used from codemap.py ***/

RPY_EXTERN
long pypy_jit_depthmap_add(unsigned long addr, unsigned int size,
                           unsigned int stackdepth)
{
    skipnode_t *new = skiplist_malloc(sizeof(depthmap_data_t));
    depthmap_data_t *data;
    if (new == NULL)
        return -1;   /* too bad */

    new->key = addr;
    data = (depthmap_data_t *)new->data;
    data->block_size = size;
    data->stack_depth = stackdepth;

    pypy_codemap_invalid_set(1);
    skiplist_insert(&jit_depthmap_head, new);
    pypy_codemap_invalid_set(0);
    return 0;
}

RPY_EXTERN
void pypy_jit_depthmap_clear(unsigned long addr, unsigned int size)
{
    unsigned long search_key = addr + size - 1;
    if (size == 0)
        return;

    pypy_codemap_invalid_set(1);
    while (1) {
        /* search for all nodes belonging to the range, and remove them */
        skipnode_t *node = skiplist_search(&jit_depthmap_head, search_key);
        if (node->key < addr)
            break;   /* exhausted */
        skiplist_remove(&jit_depthmap_head, node->key);
        free(node);
    }
    pypy_codemap_invalid_set(0);
}

/*** interface used from pypy/module/_vmprof ***/

RPY_EXTERN
long pypy_jit_stack_depth_at_loc(long loc)
{
    skipnode_t *depthmap = skiplist_search(&jit_depthmap_head,
                                           (unsigned long)loc);
    depthmap_data_t *data;
    unsigned long rel_addr;

    if (depthmap == &jit_depthmap_head)
        return -1;

    rel_addr = (unsigned long)loc - depthmap->key;
    data = (depthmap_data_t *)depthmap->data;
    if (rel_addr >= data->block_size)
        return -1;

    return data->stack_depth;
}

/************************************************************/
