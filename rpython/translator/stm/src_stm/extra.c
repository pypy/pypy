/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"


void stm_copy_to_old_id_copy(gcptr obj, gcptr id)
{
    //assert(!stmgc_is_in_nursery(thread_descriptor, id));
    assert(id->h_tid & GCFLAG_OLD);

    size_t size = stmgc_size(obj);
    memcpy(id, obj, size);
    id->h_tid &= ~GCFLAG_HAS_ID;
    id->h_tid |= GCFLAG_OLD;
    dprintf(("copy_to_old_id_copy(%p -> %p)\n", obj, id));
}


void stm_clear_on_abort(void *start, size_t bytes)
{
    struct tx_descriptor *d = thread_descriptor;
    assert(d != NULL);
    d->mem_clear_on_abort = start;
    d->mem_bytes_to_clear_on_abort = bytes;
}

void stm_call_on_abort(void *key, void callback(void *))
{
    struct tx_descriptor *d = thread_descriptor;
    if (d == NULL || d->active != 1)
        return;   /* ignore callbacks if we're outside a transaction or
                     in an inevitable transaction (which cannot abort) */
    if (callback == NULL) {
        /* ignore the return value: unregistered keys can be
           "deleted" again */
        g2l_delete_item(&d->callbacks_on_abort, (gcptr)key);
    }
    else {
        /* double-registering the same key will crash */
        g2l_insert(&d->callbacks_on_abort, (gcptr)key, (gcptr)callback);
    }
}

void stm_clear_callbacks_on_abort(struct tx_descriptor *d)
{
    if (g2l_any_entry(&d->callbacks_on_abort))
        g2l_clear(&d->callbacks_on_abort);
}

void stm_invoke_callbacks_on_abort(struct tx_descriptor *d)
{
    wlog_t *item;
    G2L_LOOP_FORWARD(d->callbacks_on_abort, item) {
        void *key = (void *)item->addr;
        void (*callback)(void *) = (void(*)(void *))item->val;
        assert(key != NULL);
        assert(callback != NULL);

        callback(key);

    } G2L_LOOP_END;
}


intptr_t stm_allocate_public_integer_address(gcptr obj)
{
    struct tx_descriptor *d = thread_descriptor;
    gcptr stub;
    intptr_t result;
    /* plan: we allocate a small stub whose reference
       we never give to the caller except in the form 
       of an integer.
       During major collections, we visit them and update
       their references. */

    /* we don't want to deal with young objs */
    if (!(obj->h_tid & GCFLAG_OLD)) {
        stm_push_root(obj);
        stm_minor_collect();
        obj = stm_pop_root();
    }
    assert(obj->h_tid & GCFLAG_OLD);

    spinlock_acquire(d->public_descriptor->collection_lock, 'P');

    stub = stm_stub_malloc(d->public_descriptor, 0);
    stub->h_tid = (obj->h_tid & STM_USER_TID_MASK)
        | GCFLAG_PUBLIC | GCFLAG_STUB | GCFLAG_SMALLSTUB
        | GCFLAG_OLD;

    stub->h_revision = ((revision_t)obj) | 2;
    if (!(obj->h_tid & GCFLAG_PREBUILT_ORIGINAL) && obj->h_original) {
        stub->h_original = obj->h_original;
    }
    else {
        stub->h_original = (revision_t)obj;
    }

    result = (intptr_t)stub;
    spinlock_release(d->public_descriptor->collection_lock);
    stm_register_integer_address(result);

    dprintf(("allocate_public_int_adr(%p): %p", obj, stub));
    return result;
}






/************************************************************/
/* Each object has a h_original pointer to an old copy of 
   the same object (e.g. an old revision), the "original". 
   The memory location of this old object is used as the ID 
   for this object. If h_original is NULL *and* it is an
   old object copy, it itself is the original. This invariant
   must be upheld by all code dealing with h_original.
   The original copy must never be moved again. Also, it may
   be just a stub-object.
   
   If we want the ID of an object which is still young,
   we must preallocate an old shadow-original that is used
   as the target of the young object in a minor collection.
   In this case, we set the HAS_ID flag on the young obj
   to notify minor_collect.
   This flag can be lost if the young obj is stolen. Then
   the stealing thread uses the shadow-original itself and
   minor_collect must not overwrite it again.
   Also, if there is already a backup-copy around, we use
   this instead of allocating another old object to use as 
   the shadow-original.
 */

static revision_t mangle_hash(revision_t n)
{
    /* To hash pointers in dictionaries.  Assumes that i shows some
       alignment (to 4, 8, maybe 16 bytes), so we use the following
       formula to avoid the trailing bits being always 0.
       This formula is reversible: two different values of 'i' will
       always give two different results.
    */
    return n ^ (((urevision_t)n) >> 4);
}


revision_t stm_hash(gcptr p)
{
    /* Prebuilt objects may have a specific hash stored in an extra 
       field. For now, we will simply always follow h_original and
       see, if it is a prebuilt object (XXX: maybe propagate a flag
       to all copies of a prebuilt to avoid this cache miss).
     */
    if (p->h_original) {
        if (p->h_tid & GCFLAG_PREBUILT_ORIGINAL) {
            return p->h_original;
        }
        gcptr orig = (gcptr)p->h_original;
        if ((orig->h_tid & GCFLAG_PREBUILT_ORIGINAL) && orig->h_original) {
            return orig->h_original;
        }
    }
    return mangle_hash(stm_id(p));
}


revision_t stm_id(gcptr p)
{
    struct tx_descriptor *d = thread_descriptor;
    revision_t result;

    if (p->h_original) { /* fast path */
        if (p->h_tid & GCFLAG_PREBUILT_ORIGINAL) {
            /* h_original may contain a specific hash value,
               but in case of the prebuilt original version, 
               its memory location is the id */
            return (revision_t)p;
        }

        assert(p->h_original != (revision_t)p);

        dprintf(("stm_id(%p) has orig fst: %p\n", 
                 p, (gcptr)p->h_original));
        return p->h_original;
    } 
    else if (p->h_tid & GCFLAG_OLD) {
        /* old objects must have an h_original xOR be
           the original itself. */
        dprintf(("stm_id(%p) is old, orig=0 fst: %p\n", p, p));
        return (revision_t)p;
    }
    
    spinlock_acquire(d->public_descriptor->collection_lock, 'I');
    /* old objects must have an h_original xOR be
       the original itself. 
       if some thread stole p when it was still young,
       it must have set h_original. stealing an old obj
       makes the old obj "original".
    */
    if (p->h_original) { /* maybe now? */
        result = p->h_original;
        dprintf(("stm_id(%p) has orig: %p\n", 
                 p, (gcptr)p->h_original));
    }
    else {
        /* must create shadow original object XXX: or use
           backup, if exists */
        gcptr O = (gcptr)stmgcpage_malloc(stmgc_size(p));
        memcpy(O, p, stmgc_size(p)); /* at least major collections
                                      depend on some content of id_copy.
                                      remove after fixing that XXX */
        O->h_tid |= GCFLAG_OLD;

        p->h_original = (revision_t)O;
        p->h_tid |= GCFLAG_HAS_ID;
        
        if (p->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED) {
            gcptr B = (gcptr)p->h_revision;
            /* not stolen already: */
            assert(!(B->h_tid & GCFLAG_PUBLIC));
            B->h_original = (revision_t)O;
        }
        
        result = (revision_t)O;
        dprintf(("stm_id(%p) young, make shadow %p\n", p, O));
    }
    
    spinlock_release(d->public_descriptor->collection_lock);
    return result;
}

_Bool stm_pointer_equal(gcptr p1, gcptr p2)
{
    if (p1 != NULL && p2 != NULL) {
        /* resolve h_original, but only if !PREBUILT_ORIGINAL */
        if (p1->h_original && !(p1->h_tid & GCFLAG_PREBUILT_ORIGINAL)) {
            p1 = (gcptr)p1->h_original;
        }
        if (p2->h_original && !(p2->h_tid & GCFLAG_PREBUILT_ORIGINAL)) {
            p2 = (gcptr)p2->h_original;
        }
    }
    return (p1 == p2);
}

_Bool stm_pointer_equal_prebuilt(gcptr p1, gcptr p2)
{
    assert(p2 != NULL);
    assert(p2->h_tid & GCFLAG_PREBUILT_ORIGINAL);

    if (p1 == p2)
        return 1;

    /* the only possible case to still get True is if p2 == p1->h_original */
    return (p1 != NULL) && (p1->h_original == (revision_t)p2) &&
        !(p1->h_tid & GCFLAG_PREBUILT_ORIGINAL);
}

/************************************************************/

void stm_abort_info_push(gcptr obj, long fieldoffsets[])
{
    struct tx_descriptor *d = thread_descriptor;
    obj = stm_read_barrier(obj);
    gcptrlist_insert2(&d->abortinfo, obj, (gcptr)fieldoffsets);
}

void stm_abort_info_pop(long count)
{
    struct tx_descriptor *d = thread_descriptor;
    long newsize = d->abortinfo.size - 2 * count;
    gcptrlist_reduce_size(&d->abortinfo, newsize < 0 ? 0 : newsize);
}

size_t stm_decode_abort_info(struct tx_descriptor *d, long long elapsed_time,
                             int abort_reason, struct tx_abort_info *output)
{
    /* Re-encodes the abort info as a single tx_abort_info structure.
       This struct tx_abort_info is not visible to the outside, and used
       only as an intermediate format that is fast to generate and without
       requiring stm_read_barrier().
     */
    if (output != NULL) {
        output->signature_packed = 127;
        output->elapsed_time = elapsed_time;
        output->abort_reason = abort_reason;
        output->active = d->active;
        output->atomic = d->atomic;
        output->count_reads = d->count_reads;
        output->reads_size_limit_nonatomic = d->reads_size_limit_nonatomic;
    }

    long num_words = 0;
#define WRITE_WORD(word)   {                            \
        if (output) output->words[num_words] = (word);  \
        num_words++;                                    \
    }

    long i;
    for (i=0; i<d->abortinfo.size; i+=2) {
        char *object = (char*)stm_repeat_read_barrier(d->abortinfo.items[i+0]);
        long *fieldoffsets = (long*)d->abortinfo.items[i+1];
        long kind, offset;
        while (*fieldoffsets != 0) {
            kind = *fieldoffsets++;
            WRITE_WORD(kind);
            if (kind < 0) {
                /* -1 is start of sublist; -2 is end of sublist */
                continue;
            }
            offset = *fieldoffsets++;
            switch(kind) {
            case 1:    /* signed */
            case 2:    /* unsigned */
                WRITE_WORD(*(long *)(object + offset));
                break;
            case 3:    /* a string of bytes from the target object */
                WRITE_WORD((revision_t)*(char **)(object + offset));
                offset = *fieldoffsets++;   /* offset of len in the string */
                WRITE_WORD(offset);
                break;
            default:
                stm_fatalerror("corrupted abort log\n");
            }
        }
    }
    WRITE_WORD(0);
#undef WRITE_WORD
    return sizeof(struct tx_abort_info) + (num_words - 1) * sizeof(revision_t);
}

static size_t unpack_abort_info(struct tx_descriptor *d,
                                struct tx_abort_info *ai,
                                char *output)
{
    /* Lazily decodes a struct tx_abort_info into a single plain string.
       For convenience (no escaping needed, no limit on integer
       sizes, etc.) we follow the bittorrent format.  This makes the
       format a bit more flexible for future changes.  The struct
       tx_abort_info is still needed as an intermediate step, because
       the string parameters may not be readable during an abort
       (they may be stubs).
    */
    size_t totalsize = 0;
    char buffer[32];
    size_t res_size;
#define WRITE(c)   { totalsize++; if (output) *output++=(c); }
#define WRITE_BUF(p, sz)  { totalsize += (sz);                          \
                            if (output) {                               \
                                 memcpy(output, (p), (sz)); output += (sz); \
                             }                                          \
                           }
    WRITE('l');
    WRITE('l');
    res_size = sprintf(buffer, "i%llde", (long long)ai->elapsed_time);
    WRITE_BUF(buffer, res_size);
    res_size = sprintf(buffer, "i%de", (int)ai->abort_reason);
    WRITE_BUF(buffer, res_size);
    res_size = sprintf(buffer, "i%lde", (long)d->public_descriptor_index);
    WRITE_BUF(buffer, res_size);
    res_size = sprintf(buffer, "i%lde", (long)ai->atomic);
    WRITE_BUF(buffer, res_size);
    res_size = sprintf(buffer, "i%de", (int)ai->active);
    WRITE_BUF(buffer, res_size);
    res_size = sprintf(buffer, "i%lue", (unsigned long)ai->count_reads);
    WRITE_BUF(buffer, res_size);
    res_size = sprintf(buffer, "i%lue",
                       (unsigned long)ai->reads_size_limit_nonatomic);
    WRITE_BUF(buffer, res_size);
    WRITE('e');

    revision_t *src = ai->words;
    while (*src != 0) {
        long signed_value;
        unsigned long unsigned_value;
        char *rps;
        long offset, rps_size;

        switch (*src++) {

        case -2:
            WRITE('l');    /* '[', start of sublist */
            break;

        case -1:
            WRITE('e');    /* ']', end of sublist */
            break;

        case 1:    /* signed */
            signed_value = (long)(*src++);
            res_size = sprintf(buffer, "i%lde", signed_value);
            WRITE_BUF(buffer, res_size);
            break;

        case 2:    /* unsigned */
            unsigned_value = (unsigned long)(*src++);
            res_size = sprintf(buffer, "i%lue", unsigned_value);
            WRITE_BUF(buffer, res_size);
            break;

        case 3:    /* a string of bytes from the target object */
            rps = (char *)(*src++);
            offset = *src++;
            if (rps) {
                rps = (char *)stm_read_barrier((gcptr)rps);
                /* xxx a bit ad-hoc: it's a string whose length is a
                 * long at 'rps_size'; the string data follows
                 * immediately the length */
                rps_size = *(long *)(rps + offset);
                assert(rps_size >= 0);
                res_size = sprintf(buffer, "%ld:", rps_size);
                WRITE_BUF(buffer, res_size);
                WRITE_BUF(rps + offset + sizeof(long), rps_size);
            }
            else {
                /* write NULL as an empty string, good enough for now */
                WRITE_BUF("0:", 2);
            }
            break;

        default:
            stm_fatalerror("corrupted abort log\n");
        }
    }
    WRITE('e');
    WRITE('\0');   /* final null character */
#undef WRITE
#undef WRITE_BUF
    return totalsize;
}

char *stm_inspect_abort_info(void)
{
    struct tx_descriptor *d = thread_descriptor;
    if (d->longest_abort_info_time <= 0)
        return NULL;

    struct tx_abort_info *ai = (struct tx_abort_info *)d->longest_abort_info;
    assert(ai->signature_packed == 127);

    stm_become_inevitable("stm_inspect_abort_info");

    size_t size = unpack_abort_info(d, ai, NULL);
    char *text = malloc(size);
    if (text == NULL)
        return NULL;   /* out of memory */
    if (unpack_abort_info(d, ai, text) != size)
        stm_fatalerror("stm_inspect_abort_info: "
                       "object mutated unexpectedly\n");
    free(ai);
    d->longest_abort_info = text;
    d->longest_abort_info_time = 0;
    return d->longest_abort_info;
}

void stm_visit_abort_info(struct tx_descriptor *d, void (*visit)(gcptr *))
{
    long i, size = d->abortinfo.size;
    gcptr *items = d->abortinfo.items;
    for (i = 0; i < size; i += 2) {
        visit(&items[i]);
        /* items[i+1] is not a gc ptr */
    }

    struct tx_abort_info *ai = (struct tx_abort_info *)d->longest_abort_info;
    if (ai != NULL && ai->signature_packed == 127) {
        revision_t *src = ai->words;
        while (*src != 0) {
            gcptr *rpps;

            switch (*src++) {

            case 1:    /* signed */
            case 2:    /* unsigned */
                src++;        /* ignore the value */
                break;

            case 3:
                rpps = (gcptr *)(src++);
                src++;        /* ignore the offset */
                visit(rpps);  /* visit() the string object */
                break;
            }
        }
    }
}
