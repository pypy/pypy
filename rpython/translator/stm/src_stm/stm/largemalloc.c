/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif
/* This contains a lot of inspiration from malloc() in the GNU C Library.
   More precisely, this is (a subset of) the part that handles large
   blocks, which in our case means at least 288 bytes.  It is actually
   a general allocator, although it doesn't contain any of the small-
   or medium-block support that are also present in the GNU C Library.
*/

#define largebin_index(sz)                                      \
    (((sz) < (48 <<  6)) ?      ((sz) >>  6):  /*  0 - 47 */    \
     ((sz) < (24 <<  9)) ? 42 + ((sz) >>  9):  /* 48 - 65 */    \
     ((sz) < (12 << 12)) ? 63 + ((sz) >> 12):  /* 66 - 74 */    \
     ((sz) < (6  << 15)) ? 74 + ((sz) >> 15):  /* 75 - 79 */    \
     ((sz) < (3  << 18)) ? 80 + ((sz) >> 18):  /* 80 - 82 */    \
                           83)
#define N_BINS             84
#define LAST_BIN_INDEX(sz) ((sz) >= (3 << 18))

typedef struct dlist_s {
    struct dlist_s *next;   /* a circular doubly-linked list */
    struct dlist_s *prev;
} dlist_t;

typedef struct ulist_s {
    struct ulist_s *up;     /* a non-circular doubly-linked list */
    struct ulist_s *down;
} ulist_t;

typedef struct malloc_chunk {
    size_t prev_size;     /* - if the previous chunk is free: size of its data
                             - otherwise, if this chunk is free: 1
                             - otherwise, 0. both chunks used */
    size_t size;          /* size of the data in this chunk */

    dlist_t d;            /* if free: a doubly-linked list 'largebins' */
                          /* if not free: the user data starts here */
    ulist_t u;            /* if free, if unsorted: up==UU_UNSORTED
                             if free, if sorted: a doubly-linked list */

    /* The chunk has a total size of 'size'.  It is immediately followed
       in memory by another chunk.  This list ends with the last "chunk"
       being actually only two words long, with END_MARKER as 'size'.
       Both this last chunk and the theoretical chunk before the first
       one are considered "not free". */
} mchunk_t;

#define UU_UNSORTED          ((ulist_t *) 1)
#define THIS_CHUNK_FREE      1
#define BOTH_CHUNKS_USED     0
#define CHUNK_HEADER_SIZE    offsetof(struct malloc_chunk, d)
#define END_MARKER           0xDEADBEEF
#define MIN_ALLOC_SIZE       (sizeof(struct malloc_chunk) - CHUNK_HEADER_SIZE)

#define chunk_at_offset(p, ofs)  ((mchunk_t *)(((char *)(p)) + (ofs)))
#define data2chunk(p)            chunk_at_offset(p, -CHUNK_HEADER_SIZE)
#define updown2chunk(p)          chunk_at_offset(p,                     \
                                     -(CHUNK_HEADER_SIZE + sizeof(dlist_t)))

static mchunk_t *next_chunk(mchunk_t *p)
{
    return chunk_at_offset(p, CHUNK_HEADER_SIZE + p->size);
}


/* The free chunks are stored in "bins".  Each bin is a doubly-linked
   list of chunks.  There are 84 bins, with largebin_index() giving the
   correspondence between sizes and bin indices.

   Each free chunk is preceeded in memory by a non-free chunk (or no
   chunk at all).  Each free chunk is followed in memory by a non-free
   chunk (or no chunk at all).  Chunks are consolidated with their
   neighbors to ensure this.

   In each bin's doubly-linked list, chunks are sorted by their size in
   decreasing order (if you follow 'largebins[n].next',
   'largebins[n].next->next', etc.).  At the end of this list are some
   unsorted chunks.  All unsorted chunks are after all sorted chunks.
   Unsorted chunks are distinguished by having 'u.up == UU_UNSORTED'.

   Note that if the user always calls large_malloc() with a large
   enough argument, then the few bins corresponding to smaller values
   will never be sorted at all.  They are still populated with the
   fragments of space between bigger allocations.

   Following the 'd' linked list, we get only one chunk of every size.
   The additional chunks of a given size are linked "vertically" in
   the secondary 'u' doubly-linked list.


                            +-----+
                            | 296 |
                            +-----+
                              ^ |
                              | v
                            +-----+     +-----+
                            | 296 |     | 288 |
                            +-----+     +-----+
                              ^ |         ^ |     UU_UNSORTED
                              | v         | v          |
   largebins    +-----+     +-----+     +-----+     +-----+     largebins
   [4].next <-> | 304 | <-> | 296 | <-> | 288 | <-> | 296 | <-> [4].prev
                +-----+     +-----+     +-----+     +-----+

*/


static struct {
    uint8_t lock;
    mchunk_t *first_chunk, *last_chunk;
    dlist_t largebins[N_BINS];
} lm __attribute__((aligned(64)));


static void lm_lock(void)
{
    stm_spinlock_acquire(lm.lock);
}

static void lm_unlock(void)
{
    stm_spinlock_release(lm.lock);
}


static void insert_unsorted(mchunk_t *new)
{
    size_t index = LAST_BIN_INDEX(new->size) ? N_BINS - 1
                                             : largebin_index(new->size);
    new->d.next = &lm.largebins[index];
    new->d.prev = lm.largebins[index].prev;
    new->d.prev->next = &new->d;
    new->u.up = UU_UNSORTED;
    new->u.down = NULL;
    lm.largebins[index].prev = &new->d;
}

static int compare_chunks(const void *vchunk1, const void *vchunk2)
{
    /* sort by size */
    mchunk_t *chunk1 = *(mchunk_t *const *)vchunk1;
    mchunk_t *chunk2 = *(mchunk_t *const *)vchunk2;
    if (chunk1->size < chunk2->size)
        return -1;
    if (chunk1->size == chunk2->size)
        return 0;
    else
        return +1;
}

#define MAX_STACK_COUNT  64

static void really_sort_bin(size_t index)
{
    dlist_t *unsorted = lm.largebins[index].prev;
    dlist_t *end = &lm.largebins[index];
    dlist_t *scan = unsorted->prev;
    size_t count = 1;
    while (scan != end && data2chunk(scan)->u.up == UU_UNSORTED) {
        scan = scan->prev;
        ++count;
    }
    end->prev = scan;
    scan->next = end;

    mchunk_t *chunk1;
    mchunk_t *chunk_array[MAX_STACK_COUNT];
    mchunk_t **chunks = chunk_array;

    if (count == 1) {
        chunk1 = data2chunk(unsorted);   /* common case */
        count = 0;
    }
    else {
        if (count > MAX_STACK_COUNT) {
            chunks = malloc(count * sizeof(mchunk_t *));
            if (chunks == NULL) {
                stm_fatalerror("out of memory");   // XXX
            }
        }
        size_t i;
        for (i = 0; i < count; i++) {
            chunks[i] = data2chunk(unsorted);
            unsorted = unsorted->prev;
        }
        assert(unsorted == scan);
        qsort(chunks, count, sizeof(mchunk_t *), compare_chunks);

        chunk1 = chunks[--count];
    }
    size_t search_size = chunk1->size;
    dlist_t *head = lm.largebins[index].next;

    while (1) {
        if (head == end || data2chunk(head)->size < search_size) {
            /* insert 'chunk1' here, before the current head */
            head->prev->next = &chunk1->d;
            chunk1->d.prev = head->prev;
            head->prev = &chunk1->d;
            chunk1->d.next = head;
            chunk1->u.up = NULL;
            chunk1->u.down = NULL;
            head = &chunk1->d;
        }
        else if (data2chunk(head)->size == search_size) {
            /* insert 'chunk1' vertically in the 'u' list */
            ulist_t *uhead = &data2chunk(head)->u;
            chunk1->u.up = uhead->up;
            chunk1->u.down = uhead;
            if (uhead->up != NULL)
                uhead->up->down = &chunk1->u;
            uhead->up = &chunk1->u;
#ifndef NDEBUG
            chunk1->d.next = (dlist_t *)0x42;   /* not used */
            chunk1->d.prev = (dlist_t *)0x42;
#endif
        }
        else {
            head = head->next;
            continue;
        }
        if (count == 0)
            break;    /* all done */
        chunk1 = chunks[--count];
        search_size = chunk1->size;
    }

    if (chunks != chunk_array)
        free(chunks);
}

static void sort_bin(size_t index)
{
    dlist_t *last = lm.largebins[index].prev;
    if (last != &lm.largebins[index] && data2chunk(last)->u.up == UU_UNSORTED)
        really_sort_bin(index);
}

static void unlink_chunk(mchunk_t *mscan)
{
    if (mscan->u.down != NULL) {
        /* unlink mscan from the vertical list 'u' */
        ulist_t *up   = mscan->u.up;
        ulist_t *down = mscan->u.down;
        down->up = up;
        if (up != NULL) up->down = down;
    }
    else {
        dlist_t *prev = mscan->d.prev;
        dlist_t *next = mscan->d.next;
        if (mscan->u.up == NULL || mscan->u.up == UU_UNSORTED) {
            /* unlink mscan from the doubly-linked list 'd' */
            next->prev = prev;
            prev->next = next;
        }
        else {
            /* relink in the 'd' list the item above me */
            mchunk_t *above = updown2chunk(mscan->u.up);
            next->prev = &above->d;
            prev->next = &above->d;
            above->d.next = next;
            above->d.prev = prev;
            above->u.down = NULL;
        }
    }
}

char *_stm_large_malloc(size_t request_size)
{
    /* 'request_size' should already be a multiple of the word size here */
    assert((request_size & (sizeof(char *)-1)) == 0);

    /* it can be very small, but we need to ensure a minimal size
       (currently 32 bytes) */
    if (request_size < MIN_ALLOC_SIZE)
        request_size = MIN_ALLOC_SIZE;

    lm_lock();

    size_t index = largebin_index(request_size);
    sort_bin(index);

    /* scan through the chunks of current bin in reverse order
       to find the smallest that fits. */
    dlist_t *scan = lm.largebins[index].prev;
    dlist_t *end = &lm.largebins[index];
    mchunk_t *mscan;
    while (scan != end) {
        mscan = data2chunk(scan);
        assert(mscan->prev_size == THIS_CHUNK_FREE);
        assert(next_chunk(mscan)->prev_size == mscan->size);
        assert(IMPLY(mscan->d.prev != end,
                     data2chunk(mscan->d.prev)->size > mscan->size));

        if (mscan->size >= request_size)
            goto found;
        scan = mscan->d.prev;
    }

    /* search now through all higher bins.  We only need to take the
       smallest item of the first non-empty bin, as it will be large
       enough. */
    while (++index < N_BINS) {
        if (lm.largebins[index].prev != &lm.largebins[index]) {
            /* non-empty bin. */
            sort_bin(index);
            scan = lm.largebins[index].prev;
            mscan = data2chunk(scan);
            goto found;
        }
    }

    /* not enough memory. */
    lm_unlock();
    return NULL;

 found:
    assert(mscan->size >= request_size);
    assert(mscan->u.up != UU_UNSORTED);

    if (mscan->u.up != NULL) {
        /* fast path: grab the item that is just above, to avoid needing
           to rearrange the 'd' list */
        mchunk_t *above = updown2chunk(mscan->u.up);
        ulist_t *two_above = above->u.up;
        mscan->u.up = two_above;
        if (two_above != NULL) two_above->down = &mscan->u;
        mscan = above;
    }
    else {
        unlink_chunk(mscan);
    }

    size_t remaining_size = mscan->size - request_size;
    if (remaining_size < sizeof(struct malloc_chunk)) {
        next_chunk(mscan)->prev_size = BOTH_CHUNKS_USED;
        request_size = mscan->size;
    }
    else {
        /* only part of the chunk is being used; reduce the size
           of 'mscan' down to 'request_size', and create a new
           chunk of the 'remaining_size' afterwards */
        mchunk_t *new = chunk_at_offset(mscan, CHUNK_HEADER_SIZE +
                                               request_size);
        new->prev_size = THIS_CHUNK_FREE;
        size_t remaining_data_size = remaining_size - CHUNK_HEADER_SIZE;
        new->size = remaining_data_size;
        next_chunk(new)->prev_size = remaining_data_size;
        insert_unsorted(new);
    }
    mscan->size = request_size;
    mscan->prev_size = BOTH_CHUNKS_USED;
    increment_total_allocated(request_size + LARGE_MALLOC_OVERHEAD);
#ifndef NDEBUG
    memset((char *)&mscan->d, 0xda, request_size);
#endif

    lm_unlock();

    return (char *)&mscan->d;
}

static void _large_free(mchunk_t *chunk)
{
    assert((chunk->size & (sizeof(char *) - 1)) == 0);
    assert(chunk->prev_size != THIS_CHUNK_FREE);

    /* 'size' is at least MIN_ALLOC_SIZE */
    increment_total_allocated(-(chunk->size + LARGE_MALLOC_OVERHEAD));

#ifndef NDEBUG
    {
        char *data = (char *)&chunk->d;
        assert(chunk->size >= sizeof(dlist_t));
        assert(chunk->size <= (((char *)lm.last_chunk) - data));
        memset(data, 0xDE, chunk->size);
    }
#endif

    /* try to merge with the following chunk in memory */
    size_t msize = chunk->size + CHUNK_HEADER_SIZE;
    mchunk_t *mscan = chunk_at_offset(chunk, msize);

    if (mscan->prev_size == BOTH_CHUNKS_USED) {
        assert((mscan->size & (sizeof(char *) - 1)) == 0);
        mscan->prev_size = chunk->size;
    }
    else {
        size_t fsize = mscan->size;
        mchunk_t *fscan = chunk_at_offset(mscan, fsize + CHUNK_HEADER_SIZE);

        /* unlink the following chunk */
        unlink_chunk(mscan);

#ifndef NDEBUG
        mscan->prev_size = (size_t)-258;  /* 0xfffffffffffffefe */
        mscan->size = (size_t)-515;       /* 0xfffffffffffffdfd */
#endif

        /* merge the two chunks */
        assert(fsize == fscan->prev_size);
        fsize += msize;
        fscan->prev_size = fsize;
        chunk->size = fsize;
    }

    /* try to merge with the previous chunk in memory */
    if (chunk->prev_size == BOTH_CHUNKS_USED) {
        chunk->prev_size = THIS_CHUNK_FREE;
    }
    else {
        assert((chunk->prev_size & (sizeof(char *) - 1)) == 0);

        /* get at the previous chunk */
        msize = chunk->prev_size + CHUNK_HEADER_SIZE;
        mscan = chunk_at_offset(chunk, -msize);
        assert(mscan->prev_size == THIS_CHUNK_FREE);
        assert(mscan->size == chunk->prev_size);

        /* unlink the previous chunk */
        unlink_chunk(mscan);

        /* merge the two chunks */
        mscan->size = msize + chunk->size;
        next_chunk(mscan)->prev_size = mscan->size;

        assert(chunk->prev_size = (size_t)-1);
        assert(chunk->size = (size_t)-1);
        chunk = mscan;
    }

    insert_unsorted(chunk);
}

void _stm_large_free(char *data)
{
    lm_lock();
    _large_free(data2chunk(data));
    lm_unlock();
}


void _stm_large_dump(void)
{
    lm_lock();
    char *data = ((char *)lm.first_chunk) + 16;
    size_t prev_size_if_free = 0;
    fprintf(stderr, "\n");
    while (1) {
        assert((((uintptr_t)data) & 7) == 0);   /* alignment */
        fprintf(stderr, "[ %p: %zu", data - 16, *(size_t*)(data - 16));
        if (prev_size_if_free == 0) {
            assert(*(size_t*)(data - 16) == THIS_CHUNK_FREE ||
                   *(size_t*)(data - 16) == BOTH_CHUNKS_USED);
            if (*(size_t*)(data - 16) == THIS_CHUNK_FREE)
                prev_size_if_free = (*(size_t*)(data - 8));
        }
        else {
            assert(*(size_t*)(data - 16) == prev_size_if_free);
            prev_size_if_free = 0;
        }
        if (*(size_t*)(data - 8) == END_MARKER)
            break;
        if (prev_size_if_free) {
            fprintf(stderr, "        \t(up %p / down %p)",
                    *(void **)(data + 16), *(void **)(data + 24));
        }
        fprintf(stderr, "\n  %p: %zu ]", data - 8, *(size_t*)(data - 8));
        if (prev_size_if_free) {
            fprintf(stderr, "\t(prev %p <-> next %p)\n",
                    *(void **)(data + 8), *(void **)data);
        }
        else {
            fprintf(stderr, "\n");
        }
        assert(*(ssize_t*)(data - 8) >= 16);
        data += *(size_t*)(data - 8);
        data += 16;
    }
    fprintf(stderr, "\n  %p: end. ]\n\n", data - 8);
    assert(data - 16 == (char *)lm.last_chunk);
    lm_unlock();
}

char *_stm_largemalloc_data_start(void)
{
    return (char *)lm.first_chunk;
}

#ifdef STM_LARGEMALLOC_TEST
bool (*_stm_largemalloc_keep)(char *data);   /* a hook for tests */
#endif

void _stm_largemalloc_init_arena(char *data_start, size_t data_size)
{
    int i;
    for (i = 0; i < N_BINS; i++) {
        lm.largebins[i].prev = &lm.largebins[i];
        lm.largebins[i].next = &lm.largebins[i];
    }

    assert(data_size >= 2 * sizeof(struct malloc_chunk));
    assert((data_size & 31) == 0);
    lm.first_chunk = (mchunk_t *)data_start;
    lm.first_chunk->prev_size = THIS_CHUNK_FREE;
    lm.first_chunk->size = data_size - 2 * CHUNK_HEADER_SIZE;
    lm.last_chunk = chunk_at_offset(lm.first_chunk,
                                    data_size - CHUNK_HEADER_SIZE);
    lm.last_chunk->prev_size = lm.first_chunk->size;
    lm.last_chunk->size = END_MARKER;
    assert(lm.last_chunk == next_chunk(lm.first_chunk));
    lm.lock = 0;

    insert_unsorted(lm.first_chunk);

#ifdef STM_LARGEMALLOC_TEST
    _stm_largemalloc_keep = NULL;
#endif
}

int _stm_largemalloc_resize_arena(size_t new_size)
{
    int result = 0;
    lm_lock();

    if (new_size < 2 * sizeof(struct malloc_chunk))
        goto fail;
    OPT_ASSERT((new_size & 31) == 0);

    new_size -= CHUNK_HEADER_SIZE;
    mchunk_t *new_last_chunk = chunk_at_offset(lm.first_chunk, new_size);
    mchunk_t *old_last_chunk = lm.last_chunk;
    size_t old_size = ((char *)old_last_chunk) - (char *)lm.first_chunk;

    if (new_size < old_size) {
        /* check if there is enough free space at the end to allow
           such a reduction */
        size_t lsize = lm.last_chunk->prev_size;
        assert(lsize != THIS_CHUNK_FREE);
        if (lsize == BOTH_CHUNKS_USED)
            goto fail;
        lsize += CHUNK_HEADER_SIZE;
        mchunk_t *prev_chunk = chunk_at_offset(lm.last_chunk, -lsize);
        if (((char *)new_last_chunk) < ((char *)prev_chunk) +
                                       sizeof(struct malloc_chunk))
            goto fail;

        /* unlink the prev_chunk from the doubly-linked list */
        unlink_chunk(prev_chunk);

        /* reduce the prev_chunk */
        assert(prev_chunk->size == lm.last_chunk->prev_size);
        prev_chunk->size = ((char*)new_last_chunk) - (char *)prev_chunk
                           - CHUNK_HEADER_SIZE;

        /* make a fresh-new last chunk */
        new_last_chunk->prev_size = prev_chunk->size;
        new_last_chunk->size = END_MARKER;
        lm.last_chunk = new_last_chunk;
        assert(lm.last_chunk == next_chunk(prev_chunk));

        insert_unsorted(prev_chunk);
    }
    else if (new_size > old_size) {
        /* make the new last chunk first, with only the extra size */
        mchunk_t *old_last_chunk = lm.last_chunk;
        old_last_chunk->size = (new_size - old_size) - CHUNK_HEADER_SIZE;
        new_last_chunk->prev_size = BOTH_CHUNKS_USED;
        new_last_chunk->size = END_MARKER;
        lm.last_chunk = new_last_chunk;
        assert(lm.last_chunk == next_chunk(old_last_chunk));

        /* then free the last_chunk (turn it from "used" to "free) */
        _large_free(old_last_chunk);
    }

    result = 1;
 fail:
    lm_unlock();
    return result;
}


static inline bool _largemalloc_sweep_keep(mchunk_t *chunk)
{
#ifdef STM_LARGEMALLOC_TEST
    if (_stm_largemalloc_keep != NULL)
        return _stm_largemalloc_keep((char *)&chunk->d);
#endif
    return largemalloc_keep_object_at((char *)&chunk->d);
}

void _stm_largemalloc_sweep(void)
{
    lm_lock();

    /* This may be slightly optimized by inlining _large_free() and
       making cases, e.g. we might know already if the previous block
       was free or not.  It's probably not really worth it. */
    mchunk_t *mnext, *chunk = lm.first_chunk;

    if (chunk->prev_size == THIS_CHUNK_FREE)
        chunk = next_chunk(chunk);   /* go to the first non-free chunk */

    while (chunk != lm.last_chunk) {
        /* here, the chunk we're pointing to is not free */
        assert(chunk->prev_size != THIS_CHUNK_FREE);

        /* first figure out the next non-free chunk */
        mnext = next_chunk(chunk);
        if (mnext->prev_size == THIS_CHUNK_FREE)
            mnext = next_chunk(mnext);

        /* use the callback to know if 'chunk' contains an object that
           survives or dies */
        if (!_largemalloc_sweep_keep(chunk)) {
            dprintf(("dies: %p\n", (char*)((char*)&chunk->d - stm_object_pages)));
            _large_free(chunk);     /* dies */
        }
        chunk = mnext;
    }

    lm_unlock();
}
