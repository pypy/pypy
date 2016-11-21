/* Imported by rpython/translator/stm/import_stmgc.py */
/*
Design of stmgc's "hashtable" objects
=====================================
A "hashtable" is theoretically a lazily-filled array of objects of
length 2**64.  Initially it is full of NULLs.  It's obviously
implemented as a dictionary in which NULL objects are not needed.

A real dictionary can be implemented on top of it, by using the index
`hash(key)` in the hashtable, and storing a list of `(key, value)`
pairs at that index (usually only one, unless there is a hash
collision).

The main operations on a hashtable are reading or writing an object at a
given index.  It also supports fetching the list of non-NULL entries.

There are two markers for every index (a read and a write marker).
This is unlike regular arrays, which have only two markers in total.

Additionally, we use the read marker for the hashtable object itself
to mean "we have read the complete list of keys".  This plays the role
of a "global" read marker: when any thread adds a new key/value object
to the hashtable, this new object's read marker is initialized with a
copy of the "global" read marker --- in all segments.


Implementation
--------------

First idea: have the hashtable in raw memory, pointing to "entry"
objects (which are regular, GC- and STM-managed objects).  The entry
objects themselves point to the user-specified objects.  The entry
objects hold the read/write markers.  Every entry object, once
created, stays around.  It is only removed by the next major GC if it
points to NULL and its read/write markers are not set in any
currently-running transaction.

References
----------

Inspired by: http://ppl.stanford.edu/papers/podc011-bronson.pdf
*/
#include <stdint.h>

uint32_t stm_hashtable_entry_userdata;


#define INITIAL_HASHTABLE_SIZE   8
#define PERTURB_SHIFT            5
#define RESIZING_LOCK            0

#define TRACE_FLAG_OFF              0
#define TRACE_FLAG_ONCE             1
#define TRACE_FLAG_KEEPALIVE        2

struct stm_hashtable_table_s {
    uintptr_t mask;      /* 'mask' is always immutable. */

    /* 'resize_counter' start at an odd value, and is decremented (by
       6) for every new item put in 'items'.  When it crosses 0, we
       instead allocate a bigger table and change 'resize_counter' to
       be a regular pointer to it (which is then even).  The whole
       structure is immutable then.

       The field 'resize_counter' also works as a write lock: changes
       go via the intermediate value RESIZING_LOCK (0).
    */
    uintptr_t resize_counter;

    uint8_t trace_flag;

    stm_hashtable_entry_t *items[INITIAL_HASHTABLE_SIZE];
};

#define IS_EVEN(p) (((p) & 1) == 0)

struct stm_hashtable_s {
    stm_hashtable_table_t *table;
    stm_hashtable_table_t initial_table;
    uint64_t additions;
    uint64_t pickitem_index;
};


static inline void init_table(stm_hashtable_table_t *table, uintptr_t itemcount)
{
    table->mask = itemcount - 1;
    table->resize_counter = itemcount * 4 + 1;
    table->trace_flag = TRACE_FLAG_OFF;
    memset(table->items, 0, itemcount * sizeof(stm_hashtable_entry_t *));
}

stm_hashtable_t *stm_hashtable_create(void)
{
    stm_hashtable_t *hashtable = malloc(sizeof(stm_hashtable_t));
    assert(hashtable);
    hashtable->table = &hashtable->initial_table;
    hashtable->additions = 0;
    init_table(&hashtable->initial_table, INITIAL_HASHTABLE_SIZE);
    return hashtable;
}

void stm_hashtable_free(stm_hashtable_t *hashtable)
{
    uintptr_t rc = hashtable->initial_table.resize_counter;
    free(hashtable);
    while (IS_EVEN(rc)) {
        assert(rc != RESIZING_LOCK);

        stm_hashtable_table_t *table = (stm_hashtable_table_t *)rc;
        rc = table->resize_counter;
        free(table);
    }
}

static bool _stm_was_read_by_anybody(object_t *obj)
{
    /* can only be safely called during major GC, when all other threads
       are suspended */
    assert(_has_mutex());

    long i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        if (get_priv_segment(i)->transaction_state == TS_NONE)
            continue;
        if (was_read_remote(get_segment_base(i), obj))
            return true;
    }
    return false;
}

#define VOLATILE_HASHTABLE(p)    ((volatile stm_hashtable_t *)(p))
#define VOLATILE_TABLE(p)  ((volatile stm_hashtable_table_t *)(p))

static void _insert_clean(stm_hashtable_table_t *table,
                          stm_hashtable_entry_t *entry,
                          uintptr_t index)
{
    uintptr_t mask = table->mask;
    uintptr_t i = index & mask;
    if (table->items[i] == NULL) {
        table->items[i] = entry;
        return;
    }

    uintptr_t perturb = index;
    while (1) {
        i = (i << 2) + i + perturb + 1;
        i &= mask;
        if (table->items[i] == NULL) {
            table->items[i] = entry;
            return;
        }

        perturb >>= PERTURB_SHIFT;
    }
}

static void _stm_rehash_hashtable(stm_hashtable_t *hashtable,
                                  uintptr_t biggercount,
                                  long segnum) /* segnum=-1 if no major GC */
{
    char *segment_base = segnum == -1 ? NULL : get_segment_base(segnum);
    dprintf(("rehash %p to size %ld, segment_base=%p\n",
             hashtable, biggercount, segment_base));

    size_t size = (offsetof(stm_hashtable_table_t, items)
                   + biggercount * sizeof(stm_hashtable_entry_t *));
    stm_hashtable_table_t *biggertable = malloc(size);
    assert(biggertable);   // XXX

    stm_hashtable_table_t *table = hashtable->table;
    table->trace_flag = TRACE_FLAG_ONCE;
    table->resize_counter = (uintptr_t)biggertable;
    /* ^^^ this unlocks the table by writing a non-zero value to
       table->resize_counter, but the new value is a pointer to the
       new bigger table, so IS_EVEN() is still true */
    assert(IS_EVEN(table->resize_counter));

    init_table(biggertable, biggercount);

    uintptr_t j, mask = table->mask;
    uintptr_t rc = biggertable->resize_counter;
    for (j = 0; j <= mask; j++) {
        stm_hashtable_entry_t *entry = table->items[j];
        if (entry == NULL)
            continue;

        char *to_read_from = segment_base;
        if (segnum != -1) {
            /* -> compaction during major GC */
            /* it's possible that we just created this entry, and it wasn't
               touched in this segment yet. Then seg0 is up-to-date.  */
            to_read_from = get_page_status_in(segnum, (uintptr_t)entry / 4096UL) == PAGE_NO_ACCESS
                ? stm_object_pages : to_read_from;
            if (((struct stm_hashtable_entry_s *)
                 REAL_ADDRESS(to_read_from, entry))->object == NULL &&
                !_stm_was_read_by_anybody((object_t *)entry)) {
                dprintf(("  removing dead %p at %ld\n", entry, j));
                continue;
            }
        }

        uintptr_t eindex;
        if (segnum == -1)
            eindex = entry->index;   /* read from STM_SEGMENT */
        else
            eindex = ((struct stm_hashtable_entry_s *)
                       REAL_ADDRESS(to_read_from, entry))->index;

        dprintf(("  insert_clean %p at index=%ld\n",
                 entry, eindex));
        _insert_clean(biggertable, entry, eindex);
        assert(rc > 6);
        rc -= 6;
    }
    biggertable->resize_counter = rc;

    stm_write_fence();   /* make sure that 'biggertable' is valid here,
                        and make sure 'table->resize_counter' is updated
                        ('table' must be immutable from now on). */
    VOLATILE_HASHTABLE(hashtable)->table = biggertable;
}

stm_hashtable_entry_t *stm_hashtable_lookup(object_t *hashtableobj,
                                            stm_hashtable_t *hashtable,
                                            uintptr_t index)
{
    stm_hashtable_table_t *table;
    uintptr_t mask;
    uintptr_t i;
    stm_hashtable_entry_t *entry;

 restart:
    /* classical dict lookup logic */
    table = VOLATILE_HASHTABLE(hashtable)->table;
    mask = table->mask;      /* read-only field */
    i = index & mask;
    entry = VOLATILE_TABLE(table)->items[i];
    if (entry != NULL) {
        if (entry->index == index) {
            stm_read((object_t*)entry);
            return entry;           /* found at the first try */
        }

        uintptr_t perturb = index;
        while (1) {
            i = (i << 2) + i + perturb + 1;
            i &= mask;
            entry = VOLATILE_TABLE(table)->items[i];
            if (entry != NULL) {
                if (entry->index == index) {
                    stm_read((object_t*)entry);
                    return entry;    /* found */
                }
            }
            else
                break;
            perturb >>= PERTURB_SHIFT;
        }
    }
    /* here, we didn't find the 'entry' with the correct index.  Note
       that even if the same 'table' is modified or resized by other
       threads concurrently, any new item found from a race condition
       would anyway contain NULL in the present segment (ensured by
       the first write_fence() below).  If the 'table' grows an entry
       just after we checked above, then we go ahead and lock the
       table; but after we get the lock, we will notice the new entry
       (ensured by the second write_fence() below) and restart the
       whole process.
     */

    uintptr_t rc = VOLATILE_TABLE(table)->resize_counter;

    /* if rc is RESIZING_LOCK (which is 0, so even), a concurrent thread
       is writing to the hashtable.  Or, if rc is another even number, it is
       actually a pointer to the next version of the table, installed
       just now.  In both cases, this thread must simply spin loop.
    */
    if (IS_EVEN(rc)) {
        stm_spin_loop();
        goto restart;
    }
    /* in the other cases, we need to grab the RESIZING_LOCK.
     */
    if (!__sync_bool_compare_and_swap(&table->resize_counter,
                                      rc, RESIZING_LOCK)) {
        goto restart;
    }
    /* we now have the lock.  The only table with a non-even value of
       'resize_counter' should be the last one in the chain, so if we
       succeeded in locking it, check this. */
    assert(table == hashtable->table);

    /* Check that 'table->items[i]' is still NULL,
       i.e. hasn't been populated under our feet.
    */
    if (table->items[i] != NULL) {
        table->resize_counter = rc;    /* unlock */
        goto restart;
    }
    /* if rc is greater than 6, there is enough room for a new
       item in the current table.
    */
    if (rc > 6) {
        /* we can only enter here once!  If we allocate stuff, we may
           run the GC, and so 'hashtableobj' might move afterwards. */
        if (_is_in_nursery(hashtableobj)
            && will_allocate_in_nursery(sizeof(stm_hashtable_entry_t))) {
            /* this also means that the hashtable is from this
               transaction and not visible to other segments yet, so
               the new entry can be nursery-allocated. */
            entry = (stm_hashtable_entry_t *)
                stm_allocate(sizeof(stm_hashtable_entry_t));
            entry->userdata = stm_hashtable_entry_userdata;
            entry->index = index;
            entry->object = NULL;
        }
        else {
            /* for a non-nursery 'hashtableobj', we pretend that the
               'entry' object we're about to return was already
               existing all along, with NULL in all segments.  If the
               caller of this function is going to modify the 'object'
               field, it will call stm_write(entry) first, which will
               correctly schedule 'entry' for write propagation.  We
               do that even if 'hashtableobj' was created by the
               running transaction: the new 'entry' object is created
               as if it was older than the transaction.

               Note the following difference: if 'hashtableobj' is
               still in the nursery (case above), the 'entry' object
               is also allocated from the nursery, and after a minor
               collection it ages as an old-but-created-by-the-
               current-transaction object.  We could try to emulate
               this here, or to create young 'entry' objects, but
               doing either of these would require careful
               synchronization with other pieces of the code that may
               change.
            */
            struct stm_hashtable_entry_s initial = {
                .userdata = stm_hashtable_entry_userdata,
                .index = index,
                .object = NULL
            };
            entry = (stm_hashtable_entry_t *)
                stm_allocate_preexisting(sizeof(stm_hashtable_entry_t),
                                         (char *)&initial.header);
            hashtable->additions++;
        }
        table->items[i] = entry;
        stm_write_fence();     /* make sure 'table->items' is written here */
        VOLATILE_TABLE(table)->resize_counter = rc - 6;    /* unlock */
        stm_read((object_t*)entry);
        return entry;
    }
    else {
        /* if rc is smaller than 6, we must allocate a new bigger table.
         */
        uintptr_t biggercount = table->mask + 1;
        if (biggercount < 50000)
            biggercount *= 4;
        else
            biggercount *= 2;
        _stm_rehash_hashtable(hashtable, biggercount, /*segnum=*/-1);
        goto restart;
    }
}

object_t *stm_hashtable_read(object_t *hobj, stm_hashtable_t *hashtable,
                             uintptr_t key)
{
    stm_hashtable_entry_t *e = stm_hashtable_lookup(hobj, hashtable, key);
    // stm_read((object_t *)e); - done in _lookup()
    return e->object;
}

void stm_hashtable_write_entry(object_t *hobj, stm_hashtable_entry_t *entry,
                               object_t *nvalue)
{
    if (_STM_WRITE_CHECK_SLOWPATH((object_t *)entry)) {

        stm_write((object_t *)entry);

        /* this restriction may be lifted, see test_new_entry_if_nursery_full: */
        assert(IMPLY(_is_young((object_t *)entry), _is_young(hobj)));

        uintptr_t i = list_count(STM_PSEGMENT->modified_old_objects);
        if (i > 0 && list_item(STM_PSEGMENT->modified_old_objects, i - 3)
                     == (uintptr_t)entry) {
            /* The stm_write() above recorded a write to 'entry'.  Here,
               we add another stm_undo_s to modified_old_objects with
               TYPE_MODIFIED_HASHTABLE.  It is ignored everywhere except
               in _stm_validate().

               The goal is that this TYPE_MODIFIED_HASHTABLE ends up in
               the commit log's 'cl_written' array.  Later, another
               transaction validating that log will check two things:

               - the regular stm_undo_s entry put by stm_write() above
                 will make the other transaction check that it didn't
                 read the same 'entry' object;

                 - the TYPE_MODIFIED_HASHTABLE entry we're adding now
                   will make the other transaction check that it didn't
                   do any stm_hashtable_list() on the complete hashtable.
            */
            acquire_modification_lock_wr(STM_SEGMENT->segment_num);
            STM_PSEGMENT->modified_old_objects = list_append3(
                STM_PSEGMENT->modified_old_objects,
                TYPE_POSITION_MARKER,      /* type1 */
                TYPE_MODIFIED_HASHTABLE,   /* type2 */
                (uintptr_t)hobj);          /* modif_hashtable */
            release_modification_lock_wr(STM_SEGMENT->segment_num);
        }
    }
    entry->object = nvalue;
}

void stm_hashtable_write(object_t *hobj, stm_hashtable_t *hashtable,
                         uintptr_t key, object_t *nvalue,
                         stm_thread_local_t *tl)
{
    STM_PUSH_ROOT(*tl, nvalue);
    STM_PUSH_ROOT(*tl, hobj);
    stm_hashtable_entry_t *e = stm_hashtable_lookup(hobj, hashtable, key);
    STM_POP_ROOT(*tl, hobj);
    STM_POP_ROOT(*tl, nvalue);
    stm_hashtable_write_entry(hobj, e, nvalue);
}

long stm_hashtable_length_upper_bound(stm_hashtable_t *hashtable)
{
    stm_hashtable_table_t *table;
    uintptr_t rc;

 restart:
    table = VOLATILE_HASHTABLE(hashtable)->table;
    rc = VOLATILE_TABLE(table)->resize_counter;
    if (IS_EVEN(rc)) {
        stm_spin_loop();
        goto restart;
    }

    uintptr_t initial_rc = (table->mask + 1) * 4 + 1;
    uintptr_t num_entries_times_6 = initial_rc - rc;
    return num_entries_times_6 / 6;
}

long stm_hashtable_list(object_t *hobj, stm_hashtable_t *hashtable,
                        stm_hashtable_entry_t * TLPREFIX *results)
{
    /* Set the read marker.  It will be left as long as we're running
       the same transaction.
    */
    stm_read(hobj);

    /* Get the table.  No synchronization is needed: we may miss some
       entries that are being added, but they would contain NULL in
       this segment anyway. */
    stm_hashtable_table_t *table = VOLATILE_HASHTABLE(hashtable)->table;

    /* Read all entries, check which ones are not NULL, count them,
       and optionally list them in 'results'.
    */
    uintptr_t i, mask = table->mask;
    stm_hashtable_entry_t *entry;
    long nresult = 0;

    if (results != NULL) {
        /* collect the results in the provided list */
        for (i = 0; i <= mask; i++) {
            entry = VOLATILE_TABLE(table)->items[i];
            if (entry != NULL) {
                stm_read((object_t *)entry);
                if (entry->object != NULL)
                    results[nresult++] = entry;
            }
        }
    }
    else {
        /* don't collect, just get the exact number of results */
        for (i = 0; i <= mask; i++) {
            entry = VOLATILE_TABLE(table)->items[i];
            if (entry != NULL) {
                stm_read((object_t *)entry);
                if (entry->object != NULL)
                    nresult++;
            }
        }
    }
    return nresult;
}

stm_hashtable_entry_t *stm_hashtable_pickitem(object_t *hobj,
                                       stm_hashtable_t *hashtable)
{
    /* We use hashtable->pickitem_index as a shared index counter (not
       initialized, any initial garbage is fine).  The goal is
       two-folds:

       - This is used to implement popitem().  Like CPython and PyPy's
         non-STM dict implementations, the goal is that repeated calls
         to pickitem() maintains a roughly O(1) time per call while
         returning different items (in the case of popitem(), the
         returned items are immediately deleted).

       - Additionally, with STM, if several threads all call
         pickitem(), this should give the best effort to distribute
         different items to different threads and thus minimize
         conflicts.  (At least that's the theory; it should be tested
         in practice.)
    */
 restart:;
    uint64_t startindex = VOLATILE_HASHTABLE(hashtable)->pickitem_index;

    /* Get the table.  No synchronization is needed: we may miss some
       entries that are being added, but they would contain NULL in
       this segment anyway. */
    stm_hashtable_table_t *table = VOLATILE_HASHTABLE(hashtable)->table;

    /* Find the first entry with a non-NULL object, starting at
       'index'. */
    uintptr_t mask = table->mask;
    uintptr_t count;
    stm_hashtable_entry_t *entry;

    for (count = 0; count <= mask; ) {
        entry = VOLATILE_TABLE(table)->items[(startindex + count) & mask];
        count++;
        if (entry != NULL && entry->object != NULL) {
            /*
               Found the next entry.  Update pickitem_index now.  If
               it was already changed under our feet, we assume that
               it is because another thread just did pickitem() too
               and is likely to have got the very same entry.  In that
               case we start again from scratch to look for the
               following entry.
            */
            if (!__sync_bool_compare_and_swap(&hashtable->pickitem_index,
                                              startindex,
                                              startindex + count))
                goto restart;

            /* Here we mark the entry as as read and return it.

               Note a difference with notably stm_hashtable_list(): we
               only call stm_read() after we checked that
               entry->object is not NULL.  If we find NULL, we don't
               mark the entry as read from this thread at all in this
               step---this is fine, as we can return a random
               different entry here.
            */
            stm_read((object_t *)entry);
            return entry;
        }
    }

    /* Didn't find any entry.  We have to be sure that the dictionary
       is empty now, in the sense that returning NULL must guarantee
       conflicts with a different thread adding items.  This is done
       by marking both the dict and all entries' read marker. */
    stm_read(hobj);

    /* Reload the table after setting the read marker */
    uintptr_t i;
    table = VOLATILE_HASHTABLE(hashtable)->table;
    mask = table->mask;
    for (i = 0; i <= mask; i++) {
        entry = VOLATILE_TABLE(table)->items[i];
        if (entry != NULL) {
            stm_read((object_t *)entry);
            assert(entry->object == NULL);
        }
    }
    return NULL;
}

static void _stm_compact_hashtable(struct object_s *hobj,
                                   stm_hashtable_t *hashtable)
{
    /* Walk the chained list that starts at 'hashtable->initial_table'
       and follows the 'resize_counter' fields.  Remove all tables
       except (1) the initial one, (2) the most recent one, and (3)
       the ones on which stm_hashtable_iter_tracefn() was called.
    */
    stm_hashtable_table_t *most_recent_table = hashtable->table;
    assert(!IS_EVEN(most_recent_table->resize_counter));
    /* set the "don't free me" flag on the most recent table */
    most_recent_table->trace_flag = TRACE_FLAG_KEEPALIVE;

    stm_hashtable_table_t *known_alive = &hashtable->initial_table;
    known_alive->trace_flag = TRACE_FLAG_OFF;
    /* a KEEPALIVE flag is ignored on the initial table: it is never
       individually freed anyway */

    while (known_alive != most_recent_table) {
        uintptr_t rc = known_alive->resize_counter;
        assert(IS_EVEN(rc));
        assert(rc != RESIZING_LOCK);

        stm_hashtable_table_t *next_table = (stm_hashtable_table_t *)rc;
        if (next_table->trace_flag != TRACE_FLAG_KEEPALIVE) {
            /* free this next table and relink the chained list to skip it */
            assert(IS_EVEN(next_table->resize_counter));
            known_alive->resize_counter = next_table->resize_counter;
            free(next_table);
        }
        else {
            /* this next table is kept alive */
            known_alive = next_table;
            known_alive->trace_flag = TRACE_FLAG_OFF;
        }
    }
    /* done the first part */

    stm_hashtable_table_t *table = hashtable->table;
    uintptr_t rc = table->resize_counter;
    assert(!IS_EVEN(rc));

    if (hashtable->additions * 4 > table->mask) {
        hashtable->additions = 0;

        /* If 'hobj' was created in some current transaction, i.e. if it is
           now an overflow object, then we have the risk that some of its
           entry objects were not created with stm_allocate_preexisting().
           In that situation, a valid workaround is to read all entry
           objects in the segment of the running transaction.  Otherwise,
           the base case is to read them all from segment zero.
        */
        long segnum = get_segment_of_linear_address((char *)hobj);
        if (!IS_OVERFLOW_OBJ(get_priv_segment(segnum), hobj))
            segnum = 0;

        uintptr_t initial_rc = (table->mask + 1) * 4 + 1;
        uintptr_t num_entries_times_6 = initial_rc - rc;
        uintptr_t count = INITIAL_HASHTABLE_SIZE;
        while (count * 4 < num_entries_times_6)
            count *= 2;
        /* sanity-check: 'num_entries_times_6 < initial_rc', and so 'count'
           can never grow larger than the current table size. */
        assert(count <= table->mask + 1);

        dprintf(("compact with %ld items:\n", num_entries_times_6 / 6));
        _stm_rehash_hashtable(hashtable, count, segnum);
    }
}

static void stm_compact_hashtables(void)
{
    uintptr_t i = all_hashtables_seen->count;
    while (i > 0) {
        i -= 2;
        _stm_compact_hashtable(
            (struct object_s *)all_hashtables_seen->items[i],
            (stm_hashtable_t *)all_hashtables_seen->items[i + 1]);
    }
}

static void _hashtable_tracefn(stm_hashtable_table_t *table,
                               void trace(object_t **))
{
    if (table->trace_flag == TRACE_FLAG_ONCE)
        table->trace_flag = TRACE_FLAG_OFF;

    uintptr_t j, mask = table->mask;
    for (j = 0; j <= mask; j++) {
        stm_hashtable_entry_t *volatile *pentry;
        pentry = &VOLATILE_TABLE(table)->items[j];
        if (*pentry != NULL) {
            trace((object_t **)pentry);
        }
    }
}

void stm_hashtable_tracefn(struct object_s *hobj, stm_hashtable_t *hashtable,
                           void trace(object_t **))
{
    if (all_hashtables_seen != NULL)
        all_hashtables_seen = list_append2(all_hashtables_seen,
                                           (uintptr_t)hobj,
                                           (uintptr_t)hashtable);

    _hashtable_tracefn(VOLATILE_HASHTABLE(hashtable)->table, trace);
}


/* Hashtable iterators */

/* TRACE_FLAG_ONCE: the table must be traced once if it supports an iterator
   TRACE_FLAG_OFF: the table is the most recent table, or has already been
       traced once
   TRACE_FLAG_KEEPALIVE: during major collection only: mark tables that
       must be kept alive because there are iterators
*/

struct stm_hashtable_table_s *stm_hashtable_iter(stm_hashtable_t *hashtable)
{
    /* Get the table.  No synchronization is needed: we may miss some
       entries that are being added, but they would contain NULL in
       this segment anyway. */
    return VOLATILE_HASHTABLE(hashtable)->table;
}

stm_hashtable_entry_t **
stm_hashtable_iter_next(object_t *hobj, stm_hashtable_table_t *table,
                        stm_hashtable_entry_t **previous)
{
    /* Set the read marker on hobj for every item, in case we have
       transaction breaks in-between.
    */
    stm_read(hobj);

    /* Get the bounds of the part of the 'stm_hashtable_entry_t *' array
       that we have to check */
    stm_hashtable_entry_t **pp, **last;
    if (previous == NULL)
        pp = table->items;
    else
        pp = previous + 1;
    last = table->items + table->mask;

    /* Find the first non-null entry */
    stm_hashtable_entry_t *entry;

    while (pp <= last) {
        entry = *(stm_hashtable_entry_t *volatile *)pp;
        if (entry != NULL) {
            stm_read((object_t *)entry);
            if (entry->object != NULL) {
                //fprintf(stderr, "stm_hashtable_iter_next(%p, %p, %p) = %p\n",
                //        hobj, table, previous, pp);
                return pp;
            }
        }
        ++pp;
    }
    //fprintf(stderr, "stm_hashtable_iter_next(%p, %p, %p) = %p\n",
    //        hobj, table, previous, NULL);
    return NULL;
}

void stm_hashtable_iter_tracefn(stm_hashtable_table_t *table,
                                void trace(object_t **))
{
    if (all_hashtables_seen == NULL) {   /* for minor collections */

        /* During minor collection, tracing the table is only required
           the first time: if it contains young objects, they must be
           kept alive and have their address updated.  We use
           TRACE_FLAG_ONCE to know that.  We don't need to do it if
           our 'table' is the latest version, because in that case it
           will be done by stm_hashtable_tracefn().  That's why
           TRACE_FLAG_ONCE is only set when a more recent table is
           attached.

           It is only needed once: non-latest-version tables are
           immutable.  We mark once all the entries as old, and
           then these now-old objects stay alive until the next
           major collection.

           Checking the flag can be done without synchronization: it
           never wrong to call _hashtable_tracefn() too much, and the
           only case where it *has to* be called occurs if the
           hashtable object is still young (and not seen by other
           threads).
        */
        if (table->trace_flag == TRACE_FLAG_ONCE)
            _hashtable_tracefn(table, trace);
    }
    else {       /* for major collections */

        /* Set this flag for _stm_compact_hashtable() */
        table->trace_flag = TRACE_FLAG_KEEPALIVE;
    }
}
