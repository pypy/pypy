/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
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
    struct dlist_s *next;   /* a doubly-linked list */
    struct dlist_s *prev;
} dlist_t;

typedef struct malloc_chunk {
    size_t prev_size;     /* - if the previous chunk is free: size of its data
                             - otherwise, if this chunk is free: 1
                             - otherwise, 0. */
    size_t size;          /* size of the data in this chunk,
                             plus optionally the FLAG_SORTED */

    dlist_t d;            /* if free: a doubly-linked list */
                          /* if not free: the user data starts here */

    /* The chunk has a total size of 'size'.  It is immediately followed
       in memory by another chunk.  This list ends with the last "chunk"
       being actually only two words long, with END_MARKER as 'size'.
       Both this last chunk and the theoretical chunk before the first
       one are considered "not free". */
} mchunk_t;

#define FLAG_SORTED          1
#define THIS_CHUNK_FREE      1
#define BOTH_CHUNKS_USED     0
#define CHUNK_HEADER_SIZE    offsetof(struct malloc_chunk, d)
#define END_MARKER           0xDEADBEEF

#define chunk_at_offset(p, ofs)  ((mchunk_t *)(((char *)(p)) + (ofs)))
#define data2chunk(p)            chunk_at_offset(p, -CHUNK_HEADER_SIZE)

static mchunk_t *next_chunk_s(mchunk_t *p)
{
    assert(p->size & FLAG_SORTED);
    return chunk_at_offset(p, CHUNK_HEADER_SIZE + p->size - FLAG_SORTED);
}
static mchunk_t *next_chunk_u(mchunk_t *p)
{
    assert(!(p->size & FLAG_SORTED));
    return chunk_at_offset(p, CHUNK_HEADER_SIZE + p->size);
}
static mchunk_t *next_chunk_a(mchunk_t *p)
{
    return chunk_at_offset(p, CHUNK_HEADER_SIZE + (p->size & ~FLAG_SORTED));
}


/* The free chunks are stored in "bins".  Each bin is a doubly-linked
   list of chunks.  There are 84 bins, with largebin_index() giving the
   correspondence between sizes and bin indices.

   Each free chunk is preceeded in memory by a non-free chunk (or no
   chunk at all).  Each free chunk is followed in memory by a non-free
   chunk (or no chunk at all).  Chunks are consolidated with their
   neighbors to ensure this.

   In each bin's doubly-linked list, chunks are sorted by their size in
   decreasing order (if you start from 'd.next').  At the end of this
   list are some unsorted chunks.  All unsorted chunks are after all
   sorted chunks.  The flag 'FLAG_SORTED' distinguishes them.

   Note that if the user always calls large_malloc() with a large
   enough argument, then the few bins corresponding to smaller values
   will never be sorted at all.  They are still populated with the
   fragments of space between bigger allocations.
*/

static dlist_t largebins[N_BINS];
static mchunk_t *first_chunk, *last_chunk;


static void insert_unsorted(mchunk_t *new)
{
    size_t index = LAST_BIN_INDEX(new->size) ? N_BINS - 1
                                             : largebin_index(new->size);
    new->d.next = &largebins[index];
    new->d.prev = largebins[index].prev;
    new->d.prev->next = &new->d;
    largebins[index].prev = &new->d;
    assert(!(new->size & FLAG_SORTED));
}

static int compare_chunks(const void *vchunk1, const void *vchunk2)
{
    /* sort by size */
    const mchunk_t *chunk1 = (const mchunk_t *)vchunk1;
    const mchunk_t *chunk2 = (const mchunk_t *)vchunk2;
    if (chunk1->size < chunk2->size)
        return -1;
    if (chunk1->size == chunk2->size)
        return 0;
    else
        return +1;
}

static void really_sort_bin(size_t index)
{
    dlist_t *unsorted = largebins[index].prev;
    dlist_t *end = &largebins[index];
    dlist_t *scan = unsorted->prev;
    size_t count = 1;
    while (scan != end && !(data2chunk(scan)->size & FLAG_SORTED)) {
        scan = scan->prev;
        ++count;
    }
    end->prev = scan;
    scan->next = end;

    mchunk_t *chunk1;
    mchunk_t *chunks[count];    /* dynamically-sized */
    if (count == 1) {
        chunk1 = data2chunk(unsorted);   /* common case */
        count = 0;
    }
    else {
        size_t i;
        for (i = 0; i < count; i++) {
            chunks[i] = data2chunk(unsorted);
            unsorted = unsorted->prev;
        }
        assert(unsorted == scan);
        qsort(chunks, count, sizeof(mchunk_t *), compare_chunks);

        chunk1 = chunks[--count];
    }
    chunk1->size |= FLAG_SORTED;
    size_t search_size = chunk1->size;
    dlist_t *head = largebins[index].next;

    while (1) {
        if (head == end || search_size >= data2chunk(head)->size) {
            /* insert 'chunk1' here, before the current head */
            head->prev->next = &chunk1->d;
            chunk1->d.prev = head->prev;
            head->prev = &chunk1->d;
            chunk1->d.next = head;
            if (count == 0)
                break;    /* all done */
            chunk1 = chunks[--count];
            chunk1->size |= FLAG_SORTED;
            search_size = chunk1->size;
        }
        else {
            head = head->next;
        }
    }
}

static void sort_bin(size_t index)
{
    dlist_t *last = largebins[index].prev;
    if (last != &largebins[index] && !(data2chunk(last)->size & FLAG_SORTED))
        really_sort_bin(index);
}

char *_stm_large_malloc(size_t request_size)
{
    /* 'request_size' should already be a multiple of the word size here */
    assert((request_size & (sizeof(char *)-1)) == 0);

    size_t index = largebin_index(request_size);
    sort_bin(index);

    /* scan through the chunks of current bin in reverse order
       to find the smallest that fits. */
    dlist_t *scan = largebins[index].prev;
    dlist_t *end = &largebins[index];
    mchunk_t *mscan;
    while (scan != end) {
        mscan = data2chunk(scan);
        assert(mscan->prev_size == THIS_CHUNK_FREE);
        assert(next_chunk_s(mscan)->prev_size == mscan->size - FLAG_SORTED);

        if (mscan->size > request_size)
            goto found;
        scan = mscan->d.prev;
    }

    /* search now through all higher bins.  We only need to take the
       smallest item of the first non-empty bin, as it will be large
       enough. */
    while (++index < N_BINS) {
        if (largebins[index].prev != &largebins[index]) {
            /* non-empty bin. */
            sort_bin(index);
            scan = largebins[index].prev;
            end = &largebins[index];
            mscan = data2chunk(scan);
            goto found;
        }
    }

    /* not enough memory. */
    return NULL;

 found:
    assert(mscan->size & FLAG_SORTED);
    assert(mscan->size > request_size);

    /* unlink mscan from the doubly-linked list */
    mscan->d.next->prev = mscan->d.prev;
    mscan->d.prev->next = mscan->d.next;

    size_t remaining_size_plus_1 = mscan->size - request_size;
    if (remaining_size_plus_1 <= sizeof(struct malloc_chunk)) {
        next_chunk_s(mscan)->prev_size = BOTH_CHUNKS_USED;
        request_size = mscan->size & ~FLAG_SORTED;
    }
    else {
        /* only part of the chunk is being used; reduce the size
           of 'mscan' down to 'request_size', and create a new
           chunk of the 'remaining_size' afterwards */
        mchunk_t *new = chunk_at_offset(mscan, CHUNK_HEADER_SIZE +
                                               request_size);
        new->prev_size = THIS_CHUNK_FREE;
        size_t remaining_size = remaining_size_plus_1 - 1 - CHUNK_HEADER_SIZE;
        new->size = remaining_size;
        next_chunk_u(new)->prev_size = remaining_size;
        insert_unsorted(new);
    }
    mscan->size = request_size;
    mscan->prev_size = BOTH_CHUNKS_USED;

    return (char *)&mscan->d;
}

void _stm_large_free(char *data)
{
    mchunk_t *chunk = data2chunk(data);
    assert((chunk->size & (sizeof(char *) - 1)) == 0);
    assert(chunk->prev_size != THIS_CHUNK_FREE);

#ifndef NDEBUG
    assert(chunk->size >= sizeof(dlist_t));
    assert(chunk->size <= (((char *)last_chunk) - (char *)data));
    memset(data, 0xDE, chunk->size);
#endif

    /* try to merge with the following chunk in memory */
    size_t msize = chunk->size + CHUNK_HEADER_SIZE;
    mchunk_t *mscan = chunk_at_offset(chunk, msize);

    if (mscan->prev_size == BOTH_CHUNKS_USED) {
        assert((mscan->size & ((sizeof(char *) - 1) & ~FLAG_SORTED)) == 0);
        mscan->prev_size = chunk->size;
    }
    else {
        mscan->size &= ~FLAG_SORTED;
        size_t fsize = mscan->size;
        mchunk_t *fscan = chunk_at_offset(mscan, fsize + CHUNK_HEADER_SIZE);

        /* unlink the following chunk */
        mscan->d.next->prev = mscan->d.prev;
        mscan->d.prev->next = mscan->d.next;
        assert((mscan->prev_size = (size_t)-258, 1));  /* 0xfffffffffffffefe */
        assert((mscan->size = (size_t)-515, 1));       /* 0xfffffffffffffdfd */

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
        assert((mscan->size & ~FLAG_SORTED) == chunk->prev_size);

        /* unlink the previous chunk */
        mscan->d.next->prev = mscan->d.prev;
        mscan->d.prev->next = mscan->d.next;

        /* merge the two chunks */
        mscan->size = msize + chunk->size;
        next_chunk_u(mscan)->prev_size = mscan->size;

        assert(chunk->prev_size = (size_t)-1);
        assert(chunk->size = (size_t)-1);
        chunk = mscan;
    }

    insert_unsorted(chunk);
}


void _stm_large_dump(void)
{
    char *data = ((char *)first_chunk) + 16;
    size_t prev_size_if_free = 0;
    while (1) {
        fprintf(stderr, "[ %p: %zu\n", data - 16, *(size_t*)(data - 16));
        if (prev_size_if_free == 0) {
            assert(*(size_t*)(data - 16) == THIS_CHUNK_FREE ||
                   *(size_t*)(data - 16) == BOTH_CHUNKS_USED);
            if (*(size_t*)(data - 16) == THIS_CHUNK_FREE)
                prev_size_if_free = (*(size_t*)(data - 8)) & ~FLAG_SORTED;
        }
        else {
            assert(*(size_t*)(data - 16) == prev_size_if_free);
            prev_size_if_free = 0;
        }
        if (*(size_t*)(data - 8) == END_MARKER)
            break;
        fprintf(stderr, "  %p: %zu ]", data - 8, *(size_t*)(data - 8));
        if (prev_size_if_free) {
            fprintf(stderr, " (free %p / %p)\n",
                    *(void **)data, *(void **)(data + 8));
        }
        else {
            fprintf(stderr, "\n");
        }
        if (!prev_size_if_free)
            assert(!((*(size_t*)(data - 8)) & FLAG_SORTED));
        assert(*(ssize_t*)(data - 8) >= 16);
        data += (*(size_t*)(data - 8)) & ~FLAG_SORTED;
        data += 16;
    }
    fprintf(stderr, "  %p: end. ]\n\n", data - 8);
    assert(data - 16 == (char *)last_chunk);
}

char *_stm_largemalloc_data_start(void)
{
    return (char *)first_chunk;
}

#ifdef STM_TESTS
bool (*_stm_largemalloc_keep)(char *data);   /* a hook for tests */
#endif

void _stm_largemalloc_init_arena(char *data_start, size_t data_size)
{
    int i;
    for (i = 0; i < N_BINS; i++) {
        largebins[i].prev = &largebins[i];
        largebins[i].next = &largebins[i];
    }

    assert(data_size >= 2 * sizeof(struct malloc_chunk));
    assert((data_size & 31) == 0);
    first_chunk = (mchunk_t *)data_start;
    first_chunk->prev_size = THIS_CHUNK_FREE;
    first_chunk->size = data_size - 2 * CHUNK_HEADER_SIZE;
    last_chunk = chunk_at_offset(first_chunk, data_size - CHUNK_HEADER_SIZE);
    last_chunk->prev_size = first_chunk->size;
    last_chunk->size = END_MARKER;
    assert(last_chunk == next_chunk_u(first_chunk));

    insert_unsorted(first_chunk);

#ifdef STM_TESTS
    _stm_largemalloc_keep = NULL;
#endif
}

int _stm_largemalloc_resize_arena(size_t new_size)
{
    if (new_size < 2 * sizeof(struct malloc_chunk))
        return 0;
    OPT_ASSERT((new_size & 31) == 0);

    new_size -= CHUNK_HEADER_SIZE;
    mchunk_t *new_last_chunk = chunk_at_offset(first_chunk, new_size);
    mchunk_t *old_last_chunk = last_chunk;
    size_t old_size = ((char *)old_last_chunk) - (char *)first_chunk;

    if (new_size < old_size) {
        /* check if there is enough free space at the end to allow
           such a reduction */
        size_t lsize = last_chunk->prev_size;
        assert(lsize != THIS_CHUNK_FREE);
        if (lsize == BOTH_CHUNKS_USED)
            return 0;
        lsize += CHUNK_HEADER_SIZE;
        mchunk_t *prev_chunk = chunk_at_offset(last_chunk, -lsize);
        if (((char *)new_last_chunk) < ((char *)prev_chunk) +
                                       sizeof(struct malloc_chunk))
            return 0;

        /* unlink the prev_chunk from the doubly-linked list */
        prev_chunk->d.next->prev = prev_chunk->d.prev;
        prev_chunk->d.prev->next = prev_chunk->d.next;

        /* reduce the prev_chunk */
        assert((prev_chunk->size & ~FLAG_SORTED) == last_chunk->prev_size);
        prev_chunk->size = ((char*)new_last_chunk) - (char *)prev_chunk
                           - CHUNK_HEADER_SIZE;

        /* make a fresh-new last chunk */
        new_last_chunk->prev_size = prev_chunk->size;
        new_last_chunk->size = END_MARKER;
        last_chunk = new_last_chunk;
        assert(last_chunk == next_chunk_u(prev_chunk));

        insert_unsorted(prev_chunk);
    }
    else if (new_size > old_size) {
        /* make the new last chunk first, with only the extra size */
        mchunk_t *old_last_chunk = last_chunk;
        old_last_chunk->size = (new_size - old_size) - CHUNK_HEADER_SIZE;
        new_last_chunk->prev_size = BOTH_CHUNKS_USED;
        new_last_chunk->size = END_MARKER;
        last_chunk = new_last_chunk;
        assert(last_chunk == next_chunk_u(old_last_chunk));

        /* then free the last_chunk (turn it from "used" to "free) */
        _stm_large_free((char *)&old_last_chunk->d);
    }
    return 1;
}


static inline bool _largemalloc_sweep_keep(mchunk_t *chunk)
{
#ifdef STM_TESTS
    if (_stm_largemalloc_keep != NULL)
        return _stm_largemalloc_keep((char *)&chunk->d);
#endif
    return largemalloc_keep_object_at((char *)&chunk->d);
}

void _stm_largemalloc_sweep(void)
{
    /* This may be slightly optimized by inlining _stm_large_free() and
       making cases, e.g. we might know already if the previous block
       was free or not.  It's probably not really worth it. */
    mchunk_t *mnext, *chunk = first_chunk;

    if (chunk->prev_size == THIS_CHUNK_FREE)
        chunk = next_chunk_a(chunk);   /* go to the first non-free chunk */

    while (chunk != last_chunk) {

        /* here, the chunk we're pointing to is not free */
        assert(chunk->prev_size != THIS_CHUNK_FREE);

        /* first figure out the next non-free chunk */
        mnext = next_chunk_u(chunk);
        if (mnext->prev_size == THIS_CHUNK_FREE)
            mnext = next_chunk_a(mnext);

        /* use the callback to know if 'chunk' contains an object that
           survives or dies */
        if (!_largemalloc_sweep_keep(chunk)) {
            size_t size = chunk->size;
            increment_total_allocated(-(size + LARGE_MALLOC_OVERHEAD));
            _stm_large_free((char *)&chunk->d);     /* dies */
        }
        chunk = mnext;
    }
}
