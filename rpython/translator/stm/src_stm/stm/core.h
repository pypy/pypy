/* Imported by rpython/translator/stm/import_stmgc.py */
#define _STM_CORE_H_

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <errno.h>
#include <pthread.h>

/************************************************************/

#ifndef STM_GC_NURSERY
# define STM_GC_NURSERY     4096          // 4MB
#endif


#define NB_PAGES            (2500*256)    // 2500MB
#define NB_SEGMENTS         STM_NB_SEGMENTS
#define NB_SEGMENTS_MAX     240    /* don't increase NB_SEGMENTS past this */
#define MAP_PAGES_FLAGS     (MAP_SHARED | MAP_ANONYMOUS | MAP_NORESERVE)
#define NB_NURSERY_PAGES    (STM_GC_NURSERY/4)

#define TOTAL_MEMORY          (NB_PAGES * 4096UL * (1 + NB_SEGMENTS))
#define READMARKER_END        ((NB_PAGES * 4096UL) >> 4)
#define FIRST_OBJECT_PAGE     ((READMARKER_END + 4095) / 4096UL)
#define FIRST_NURSERY_PAGE    FIRST_OBJECT_PAGE
#define END_NURSERY_PAGE      (FIRST_NURSERY_PAGE + NB_NURSERY_PAGES)

#define READMARKER_START      ((FIRST_OBJECT_PAGE * 4096UL) >> 4)
#define FIRST_READMARKER_PAGE (READMARKER_START / 4096UL)
#define OLD_RM_START          ((END_NURSERY_PAGE * 4096UL) >> 4)
#define FIRST_OLD_RM_PAGE     (OLD_RM_START / 4096UL)
#define NB_READMARKER_PAGES   (FIRST_OBJECT_PAGE - FIRST_READMARKER_PAGE)

#define WRITELOCK_START       ((END_NURSERY_PAGE * 4096UL) >> 4)
#define WRITELOCK_END         READMARKER_END

#define CARD_SIZE   _STM_CARD_SIZE

enum /* stm_flags */ {
    /* This flag is set on non-nursery objects.  It forces stm_write()
       to call _stm_write_slowpath().
    */
    GCFLAG_WRITE_BARRIER = _STM_GCFLAG_WRITE_BARRIER,

    /* This flag is set by gcpage.c for all objects living in
       uniformly-sized pages of small objects.
    */
    GCFLAG_SMALL_UNIFORM = 0x02,

    /* The following flag is set on nursery objects of which we asked
       the id or the identityhash.  It means that a space of the size of
       the object has already been allocated in the nonmovable part.
       The same flag is abused to mark prebuilt objects whose hash has
       been taken during translation and is statically recorded just
       after the object. */
    GCFLAG_HAS_SHADOW = 0x04,

    /* Set on objects that are large enough (_STM_MIN_CARD_OBJ_SIZE)
       to have multiple cards (at least _STM_MIN_CARD_COUNT), and that
       have at least one card marked.  This flag implies
       GCFLAG_WRITE_BARRIER. */
    GCFLAG_CARDS_SET = _STM_GCFLAG_CARDS_SET,

    /* All remaining bits of the 32-bit 'stm_flags' field are taken by
       the "overflow number".  This is a number that identifies the
       "overflow objects" from the current transaction among all old
       objects.  More precisely, overflow objects are objects from the
       current transaction that have been flushed out of the nursery,
       which occurs if the same transaction allocates too many objects.
    */
    GCFLAG_OVERFLOW_NUMBER_bit0 = 0x10   /* must be last */
};


/************************************************************/


#define STM_PSEGMENT          ((stm_priv_segment_info_t *)STM_SEGMENT)

typedef TLPREFIX struct stm_priv_segment_info_s stm_priv_segment_info_t;

struct stm_priv_segment_info_s {
    struct stm_segment_info_s pub;

    /* List of old objects (older than the current transaction) that the
       current transaction attempts to modify.  This is used to track
       the STM status: they are old objects that where written to and
       that need to be copied to other segments upon commit. */
    struct list_s *modified_old_objects;

    /* For each entry in 'modified_old_objects', we have two entries
       in the following list, which give the marker at the time we added
       the entry to modified_old_objects. */
    struct list_s *modified_old_objects_markers;
    uintptr_t modified_old_objects_markers_num_old;

    /* List of out-of-nursery objects that may contain pointers to
       nursery objects.  This is used to track the GC status: they are
       all objects outside the nursery on which an stm_write() occurred
       since the last minor collection.  This list contains exactly the
       objects without GCFLAG_WRITE_BARRIER.  If there was no minor
       collection yet in the current transaction, this is NULL,
       understood as meaning implicitly "this is the same as
       'modified_old_objects'". */
    struct list_s *objects_pointing_to_nursery;
    /* Like objects_pointing_to_nursery it holds the old objects that
       we did a stm_write_card() on. Objects can be in both lists.
       It is NULL iff objects_pointing_to_nursery is NULL. */
    struct list_s *old_objects_with_cards;

    /* List of all large, overflowed objects.  Only non-NULL after the
       current transaction spanned a minor collection. */
    struct list_s *large_overflow_objects;

    /* Set of all young objects outside the nursery ("young" in the
       sense that they should be in the nursery, but were too big for
       that). */
    struct tree_s *young_outside_nursery;

    /* Support for id and identityhash: this is a dict mapping nursery
       objects with GCFLAG_HAS_SHADOW to their future location at the
       next minor collection. */
    struct tree_s *nursery_objects_shadows;

    /* List of all young weakrefs to check in minor collections. These
       are the only weakrefs that may point to young objects and never
       contain NULL. */
    struct list_s *young_weakrefs;

    /* List of all old weakrefs to check in major collections. These
       weakrefs never point to young objects and never contain NULL. */
    struct list_s *old_weakrefs;

    /* Tree of 'key->callback' associations from stm_call_on_commit()
       and stm_call_on_abort() (respectively, array items 0 and 1) */
    struct tree_s *callbacks_on_commit_and_abort[2];

    /* Start time: to know approximately for how long a transaction has
       been running, in contention management */
    uint64_t start_time;

    /* This is the number stored in the overflowed objects (a multiple of
       GCFLAG_OVERFLOW_NUMBER_bit0).  It is incremented when the
       transaction is done, but only if we actually overflowed any
       object; otherwise, no object has got this number. */
    uint32_t overflow_number;
    bool overflow_number_has_been_used;

    /* The marker stored in the global 'write_locks' array to mean
       "this segment has modified this old object". */
    uint8_t write_lock_num;

    /* The thread's safe-point state, one of the SP_xxx constants.  The
       thread is in a "safe point" if it is not concurrently doing any
       read or change in this data structure that might cause race
       conditions in other threads. */
    uint8_t safe_point;

    /* The transaction status, one of the TS_xxx constants.  This is
       only accessed when we hold the mutex. */
    uint8_t transaction_state;

    /* Temp for minor collection */
    bool minor_collect_will_commit_now;

    /* For sleeping contention management */
    bool signal_when_done;

    /* This lock is acquired when that segment calls synchronize_object_now.
       On the rare event of a page_privatize(), the latter will acquire
       all the locks in all segments.  Otherwise, for the common case,
       it's cheap.  (The set of all 'privatization_lock' in all segments
       works like one single read-write lock, with page_privatize() acquiring
       the write lock; but this variant is more efficient for the case of
       many reads / rare writes.) */
    uint8_t privatization_lock;

    /* This lock is acquired when we mutate 'modified_old_objects' but
       we don't have the global mutex.  It is also acquired during minor
       collection.  It protects against a different thread that tries to
       get this segment's marker corresponding to some object, or to
       expand the marker into a full description. */
    uint8_t marker_lock;

    /* In case of abort, we restore the 'shadowstack' field and the
       'thread_local_obj' field. */
    struct stm_shadowentry_s *shadowstack_at_start_of_transaction;
    object_t *threadlocal_at_start_of_transaction;

    /* Already signalled to commit soon: */
    bool signalled_to_commit_soon;

    /* For debugging */
#ifndef NDEBUG
    pthread_t running_pthread;
#endif

    /* marker where this thread became inevitable */
    stm_loc_marker_t marker_inev;

    /* light finalizers */
    struct list_s *young_objects_with_light_finalizers;
    struct list_s *old_objects_with_light_finalizers;

    /* regular finalizers (objs from the current transaction only) */
    struct finalizers_s *finalizers;
};

enum /* safe_point */ {
    SP_NO_TRANSACTION=0,
    SP_RUNNING,
    SP_WAIT_FOR_C_REQUEST_REMOVED,
    SP_WAIT_FOR_C_AT_SAFE_POINT,
    SP_WAIT_FOR_C_TRANSACTION_DONE,
#ifdef STM_TESTS
    SP_WAIT_FOR_OTHER_THREAD,
#endif
};
enum /* transaction_state */ {
    TS_NONE=0,
    TS_REGULAR,
    TS_INEVITABLE,
};

static char *stm_object_pages;
static int stm_object_pages_fd;
static stm_thread_local_t *stm_all_thread_locals = NULL;

static uint8_t write_locks[WRITELOCK_END - WRITELOCK_START];

enum /* card values for write_locks */ {
    CARD_CLEAR = 0,                 /* card not used at all */
    CARD_MARKED = _STM_CARD_MARKED, /* card marked for tracing in the next gc */
    CARD_MARKED_OLD = 101,          /* card was marked before, but cleared
                                       in a GC */
};


#define REAL_ADDRESS(segment_base, src)   ((segment_base) + (uintptr_t)(src))

#define IS_OVERFLOW_OBJ(pseg, obj) (((obj)->stm_flags & -GCFLAG_OVERFLOW_NUMBER_bit0) \
                                    == (pseg)->overflow_number)

static inline uintptr_t get_index_to_card_index(uintptr_t index) {
    return (index / CARD_SIZE) + 1;
}

static inline uintptr_t get_card_index_to_index(uintptr_t card_index) {
    return (card_index - 1) * CARD_SIZE;
}


static inline uintptr_t get_write_lock_idx(uintptr_t obj) {
    uintptr_t res = (obj >> 4) - WRITELOCK_START;
    assert(res < sizeof(write_locks));
    return res;
}

static inline char *get_segment_base(long segment_num) {
    return stm_object_pages + segment_num * (NB_PAGES * 4096UL);
}

static inline
struct stm_segment_info_s *get_segment(long segment_num) {
    return (struct stm_segment_info_s *)REAL_ADDRESS(
        get_segment_base(segment_num), STM_PSEGMENT);
}

static inline
struct stm_priv_segment_info_s *get_priv_segment(long segment_num) {
    return (struct stm_priv_segment_info_s *)REAL_ADDRESS(
        get_segment_base(segment_num), STM_PSEGMENT);
}

static bool _is_tl_registered(stm_thread_local_t *tl);
static bool _seems_to_be_running_transaction(void);

static void teardown_core(void);
static void abort_with_mutex(void) __attribute__((noreturn));
static stm_thread_local_t *abort_with_mutex_no_longjmp(void);
static void abort_data_structures_from_segment_num(int segment_num);

static inline bool was_read_remote(char *base, object_t *obj,
                                   uint8_t other_transaction_read_version)
{
    uint8_t rm = ((struct stm_read_marker_s *)
                  (base + (((uintptr_t)obj) >> 4)))->rm;
    assert(rm <= other_transaction_read_version);
    return rm == other_transaction_read_version;
}

static inline void _duck(void) {
    /* put a call to _duck() between two instructions that set 0 into
       a %gs-prefixed address and that may otherwise be replaced with
       llvm.memset --- it fails later because of the prefix...
       This is not needed any more after applying the patch
       llvmfix/no-memset-creation-with-addrspace.diff. */
    asm("/* workaround for llvm bug */");
}

static void copy_object_to_shared(object_t *obj, int source_segment_num);
static void synchronize_object_now(object_t *obj, bool ignore_cards);

static inline void acquire_privatization_lock(void)
{
    uint8_t *lock = (uint8_t *)REAL_ADDRESS(STM_SEGMENT->segment_base,
                                            &STM_PSEGMENT->privatization_lock);
    spinlock_acquire(*lock);
}

static inline void release_privatization_lock(void)
{
    uint8_t *lock = (uint8_t *)REAL_ADDRESS(STM_SEGMENT->segment_base,
                                            &STM_PSEGMENT->privatization_lock);
    spinlock_release(*lock);
}

static inline void acquire_marker_lock(char *segment_base)
{
    uint8_t *lock = (uint8_t *)REAL_ADDRESS(segment_base,
                                            &STM_PSEGMENT->marker_lock);
    spinlock_acquire(*lock);
}

static inline void release_marker_lock(char *segment_base)
{
    uint8_t *lock = (uint8_t *)REAL_ADDRESS(segment_base,
                                            &STM_PSEGMENT->marker_lock);
    spinlock_release(*lock);
}
