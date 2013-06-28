/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"
#include <sys/mman.h>


#define PAGE_SIZE  4096


#ifdef _GC_DEBUG
/************************************************************/

#define MMAP_TOTAL  671088640   /* 640MB */

static pthread_mutex_t malloc_mutex = PTHREAD_MUTEX_INITIALIZER;
static char *zone_start, *zone_current = NULL, *zone_end = NULL;
static signed char accessible_pages[MMAP_TOTAL / PAGE_SIZE] = {0};


static void _stm_dbgmem(void *p, size_t sz, int prot)
{
    if (sz == 0)
        return;

    assert((ssize_t)sz > 0);
    intptr_t align = ((intptr_t)p) & (PAGE_SIZE-1);
    p = ((char *)p) - align;
    sz += align;
    dprintf(("dbgmem: %p, %ld, %d\n", p, (long)sz, prot));
    int err = mprotect(p, sz, prot);
    assert(err == 0);
}

void *stm_malloc(size_t sz)
{
    pthread_mutex_lock(&malloc_mutex);

    if (zone_current == NULL) {
        zone_start = mmap(NULL, MMAP_TOTAL, PROT_NONE,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (zone_start == NULL || zone_start == MAP_FAILED) {
            stm_fatalerror("not enough memory: mmap() failed\n");
        }
        zone_current = zone_start;
        zone_end = zone_start + MMAP_TOTAL;
        assert((MMAP_TOTAL % PAGE_SIZE) == 0);
        _stm_dbgmem(zone_start, MMAP_TOTAL, PROT_NONE);
    }

    size_t nb_pages = (sz + PAGE_SIZE - 1) / PAGE_SIZE + 1;
    char *result = zone_current;
    zone_current += nb_pages * PAGE_SIZE;
    if (zone_current > zone_end) {
        stm_fatalerror("dbgmem.c: %ld MB of memory have been exausted\n",
                       (long)(MMAP_TOTAL / (1024*1024)));
    }
    pthread_mutex_unlock(&malloc_mutex);

    result += (-sz) & (PAGE_SIZE-1);
    assert(((intptr_t)(result + sz) & (PAGE_SIZE-1)) == 0);
    _stm_dbgmem(result, sz, PROT_READ | PROT_WRITE);

    long i, base = (result - zone_start) / PAGE_SIZE;
    for (i = 0; i < nb_pages; i++)
        accessible_pages[base + i] = 42;

    dprintf(("stm_malloc(%zu): %p\n", sz, result));
    assert(((intptr_t)(result + sz) & (PAGE_SIZE-1)) == 0);
    return result;
}

void stm_free(void *p, size_t sz)
{
    assert(((intptr_t)((char *)p + sz) & (PAGE_SIZE-1)) == 0);

    size_t nb_pages = (sz + PAGE_SIZE - 1) / PAGE_SIZE + 1;
    long i, base = ((char *)p - zone_start) / PAGE_SIZE;
    assert(0 <= base && base < (MMAP_TOTAL / PAGE_SIZE));
    for (i = 0; i < nb_pages; i++) {
        assert(accessible_pages[base + i] == 42);
        accessible_pages[base + i] = -1;
    }
    memset(p, 0xDD, sz);
    _stm_dbgmem(p, sz, PROT_NONE);
}

int _stm_can_access_memory(char *p)
{
    long base = ((char *)p - zone_start) / PAGE_SIZE;
    assert(0 <= base && base < (MMAP_TOTAL / PAGE_SIZE));
    return accessible_pages[base] == 42;
}

/************************************************************/
#endif


void stm_clear_large_memory_chunk(void *base, size_t size,
                                  size_t already_cleared)
{
    char *baseaddr = base;

    if (size > 2 * PAGE_SIZE) {
        int lowbits = ((intptr_t)baseaddr) & (PAGE_SIZE-1);
        if (lowbits) {   /*  clear the initial misaligned part, if any */
            int partpage = PAGE_SIZE - lowbits;
            memset(baseaddr, 0, partpage);
            baseaddr += partpage;
            size -= partpage;
        }
        /* 'already_cleared' bytes at the end are assumed to be already
           cleared.  Reduce 'size' accordingly, but avoid getting a
           misaligned 'size'. */
        size_t length = size & (-PAGE_SIZE);
        if (already_cleared > (size - length)) {
            already_cleared -= (size - length);
            already_cleared &= -PAGE_SIZE;
            length -= already_cleared;
            size = length;
            already_cleared = 0;
        }

        int err = madvise(baseaddr, length, MADV_DONTNEED);
        if (err == 0) {   /*  madvise() worked */
            baseaddr += length;
            size -= length;
        }
    }
    if (size > already_cleared) { /* clear the final misaligned part, if any */
        memset(baseaddr, 0, size - already_cleared);
    }
}
