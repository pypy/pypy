/* Imported by rpython/translator/stm/import_stmgc.py */
/* Modification locks protect from concurrent modification of
   'modified_old_objects', page-revision-changes, ...

   Modification locks are used to prevent copying from a segment
   where either the revision of some pages is inconsistent with the
   rest, or the modified_old_objects list is being modified (bk_copys).

   Lock ordering: acquire privatization lock around acquiring a set
   of modification locks!
*/

typedef struct {
    pthread_rwlock_t lock;
#ifndef NDEBUG
    volatile bool write_locked;
#endif
} modification_lock_t __attribute__((aligned(64)));

static modification_lock_t _modlocks[NB_SEGMENTS - 1];


static void setup_modification_locks(void)
{
    int i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        if (pthread_rwlock_init(&_modlocks[i - 1].lock, NULL) != 0)
            stm_fatalerror("pthread_rwlock_init: %m");
    }
}

static void teardown_modification_locks(void)
{
    int i;
    for (i = 1; i < NB_SEGMENTS; i++)
        pthread_rwlock_destroy(&_modlocks[i - 1].lock);
    memset(_modlocks, 0, sizeof(_modlocks));
}


static inline void acquire_modification_lock_wr(int segnum)
{
    if (UNLIKELY(pthread_rwlock_wrlock(&_modlocks[segnum - 1].lock) != 0))
        stm_fatalerror("pthread_rwlock_wrlock: %m");
#ifndef NDEBUG
    assert(!_modlocks[segnum - 1].write_locked);
    _modlocks[segnum - 1].write_locked = true;
#endif
}

static inline void release_modification_lock_wr(int segnum)
{
#ifndef NDEBUG
    assert(_modlocks[segnum - 1].write_locked);
    _modlocks[segnum - 1].write_locked = false;
#endif
    if (UNLIKELY(pthread_rwlock_unlock(&_modlocks[segnum - 1].lock) != 0))
        stm_fatalerror("pthread_rwlock_unlock(wr): %m");
}

static void acquire_modification_lock_set(uint64_t readset, int write)
{
    /* acquire the modification lock in 'read' mode for all segments
       in 'readset', plus the modification lock in 'write' mode for
       the segment number 'write'.
    */
    assert(NB_SEGMENTS <= 64);
    OPT_ASSERT(readset < (1 << NB_SEGMENTS));
    assert((readset & 1) == 0);       /* segment numbers normally start at 1 */
    assert(0 <= write && write < NB_SEGMENTS);     /* use 0 to mean "nobody" */

    /* acquire locks in global order */
    readset |= (1UL << write);
    int i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        if ((readset & (1UL << i)) == 0)
            continue;
        if (i == write) {
            acquire_modification_lock_wr(write);
        }
        else {
            if (UNLIKELY(pthread_rwlock_rdlock(&_modlocks[i - 1].lock) != 0))
                stm_fatalerror("pthread_rwlock_rdlock: %m");
        }
    }
}

static void release_modification_lock_set(uint64_t readset, int write)
{
    assert(NB_SEGMENTS <= 64);
    OPT_ASSERT(readset < (1 << NB_SEGMENTS));

    /* release lock order does not matter; prefer early release of
       the write lock */
    if (write > 0) {
        release_modification_lock_wr(write);
        readset &= ~(1UL << write);
    }
    int i;
    for (i = 1; i < NB_SEGMENTS; i++) {
        if ((readset & (1UL << i)) == 0)
            continue;
        if (UNLIKELY(pthread_rwlock_unlock(&_modlocks[i - 1].lock) != 0))
            stm_fatalerror("pthread_rwlock_unlock(rd): %m");
    }
}

#ifndef NDEBUG
static bool modification_lock_check_rdlock(int segnum)
{
    assert(segnum > 0);
    if (_modlocks[segnum - 1].write_locked)
        return false;
    if (pthread_rwlock_trywrlock(&_modlocks[segnum - 1].lock) == 0) {
        pthread_rwlock_unlock(&_modlocks[segnum - 1].lock);
        return false;
    }
    return true;
}
static bool modification_lock_check_wrlock(int segnum)
{
    return segnum == 0 || _modlocks[segnum - 1].write_locked;
}
#endif
