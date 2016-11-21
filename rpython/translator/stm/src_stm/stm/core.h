/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STMGC_H
# error "must be compiled via stmgc.c"
# include "../stmgc.h"  // silence flymake
#endif

#define _STM_CORE_H_

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include "list.h"

/************************************************************/

#ifndef STM_GC_NURSERY
# define STM_GC_NURSERY     4096          // 4MB
#endif


#define NB_PAGES            (2500*256)    // 2500MB
#define NB_SEGMENTS         (STM_NB_SEGMENTS+1) /* +1 for sharing seg 0 */
#define NB_SEGMENTS_MAX     240    /* don't increase NB_SEGMENTS past this */
#define NB_NURSERY_PAGES    (STM_GC_NURSERY/4)

#define TOTAL_MEMORY          (NB_PAGES * 4096UL * NB_SEGMENTS)
#define READMARKER_END        ((NB_PAGES * 4096UL) >> 4)
#define FIRST_OBJECT_PAGE     ((READMARKER_END + 4095) / 4096UL)
#define FIRST_NURSERY_PAGE    FIRST_OBJECT_PAGE
#define END_NURSERY_PAGE      (FIRST_NURSERY_PAGE + NB_NURSERY_PAGES)
#define NB_SHARED_PAGES       (NB_PAGES - END_NURSERY_PAGE)

#define READMARKER_START      ((FIRST_OBJECT_PAGE * 4096UL) >> 4)
#define FIRST_READMARKER_PAGE (READMARKER_START / 4096UL)
#define OLD_RM_START          ((END_NURSERY_PAGE * 4096UL) >> 4)
#define FIRST_OLD_RM_PAGE     (OLD_RM_START / 4096UL)
#define NB_READMARKER_PAGES   (FIRST_OBJECT_PAGE - FIRST_READMARKER_PAGE)

#define CARD_SIZE   _STM_CARD_SIZE

enum /* stm_flags */ {
    GCFLAG_WRITE_BARRIER = _STM_GCFLAG_WRITE_BARRIER,
    GCFLAG_HAS_SHADOW = 0x02,
    GCFLAG_WB_EXECUTED = 0x04,
    GCFLAG_CARDS_SET = _STM_GCFLAG_CARDS_SET,
    GCFLAG_VISITED = 0x10,
    GCFLAG_FINALIZATION_ORDERING = 0x20,
    GCFLAG_NO_CONFLICT = _STM_GCFLAG_NO_CONFLICT,
    /* All remaining bits of the 32-bit 'stm_flags' field are taken by
       the "overflow number".  This is a number that identifies the
       "overflow objects" from the current transaction among all old
       objects.  More precisely, overflow objects are objects from the
       current transaction that have been flushed out of the nursery,
       which occurs if the same transaction allocates too many objects.
    */
    GCFLAG_OVERFLOW_NUMBER_bit0 = 0x80   /* must be last */
};

#define SYNC_QUEUE_SIZE    31

enum /* card values in read markers */ {
    CARD_CLEAR = 0,                 /* card not used at all */
    CARD_MARKED = _STM_CARD_MARKED, /* card marked for tracing in the next gc */
    /* CARD_MARKED_OLD = STM_PSEGMENT->transaction_read_version, */
    /* card was marked before, but cleared in a GC */
};



/************************************************************/


#define STM_PSEGMENT          ((stm_priv_segment_info_t *)STM_SEGMENT)

typedef TLPREFIX struct stm_priv_segment_info_s stm_priv_segment_info_t;

struct stm_priv_segment_info_s {
    struct stm_segment_info_s pub;

    /* All the old objects (older than the current transaction) that
       the current transaction attempts to modify.  This is used to
       track the STM status: these are old objects that where written
       to and that will need to be recorded in the commit log.  The
       list contains three entries for every such object, in the same
       format as 'struct stm_undo_s' below.  It can also represent a
       position marker, like 'struct stm_undo_s'.
    */
    struct list_s *modified_old_objects;
    uintptr_t position_markers_last;     /* index of most recent pos marker */
    uintptr_t position_markers_len_old;  /* length of list at last minor col */

    struct list_s *objects_pointing_to_nursery;
    struct list_s *old_objects_with_cards_set;
    struct tree_s *young_outside_nursery;
    struct tree_s *nursery_objects_shadows;

    /* List of all young weakrefs to check in minor collections. These
       are the only weakrefs that may point to young objects and never
       contain NULL. */
    struct list_s *young_weakrefs;

    /* List of all old weakrefs to check in major collections. These
       weakrefs never point to young objects and never contain NULL. */
    struct list_s *old_weakrefs;


    /* list of objects created in the current transaction and
       that survived at least one minor collection. They need
       to be synchronized to other segments on commit, but they
       do not need to be in the commit log entry.
       XXX: for now it also contains small overflow objs */
    struct list_s *large_overflow_objects;

    uint8_t privatization_lock;  // XXX KILL

    uint8_t safe_point;
    uint8_t transaction_state;

    /* Temp for minor collection */
    bool minor_collect_will_commit_now;

    struct tree_s *callbacks_on_commit_and_abort[2];
    struct tree_s *active_queues;
    uint8_t active_queues_lock;

    /* This is the number stored in the overflowed objects (a multiple of
       GCFLAG_OVERFLOW_NUMBER_bit0).  It is incremented when the
       transaction is done, but only if we actually overflowed any
       object; otherwise, no object has got this number. */
    bool overflow_number_has_been_used;
    uint32_t overflow_number;


    struct stm_commit_log_entry_s *last_commit_log_entry;

    struct stm_shadowentry_s *shadowstack_at_start_of_transaction;
    object_t *threadlocal_at_start_of_transaction;

    /* For debugging */
#ifndef NDEBUG
    pthread_t running_pthread;
#endif

    /* destructors */
    struct list_s *young_objects_with_destructors;
    struct list_s *old_objects_with_destructors;

    /* regular finalizers (objs from the current transaction only) */
    struct finalizers_s *finalizers;


    /* This is for smallmalloc.c */
    struct small_malloc_data_s small_malloc_data;

    /* The sync queue used to synchronize newly allocated objs to
       other segments */
    stm_char *sq_fragments[SYNC_QUEUE_SIZE];
    int sq_fragsizes[SYNC_QUEUE_SIZE];
    int sq_len;

    /* For nursery_mark */
    uintptr_t total_throw_away_nursery;

    /* For stm_enable_atomic() */
    uintptr_t atomic_nesting_levels;
};

enum /* safe_point */ {
    SP_NO_TRANSACTION=0,
    SP_RUNNING,
    SP_WAIT_FOR_C_REQUEST_REMOVED,
    SP_WAIT_FOR_C_AT_SAFE_POINT,
    SP_WAIT_FOR_INEV,
#ifdef STM_TESTS
    SP_WAIT_FOR_OTHER_THREAD,
#endif
};

enum /* transaction_state */ {
    TS_NONE=0,
    TS_REGULAR,
    TS_INEVITABLE,
};

#define MSG_INEV_DONT_SLEEP  ((const char *)1)

#define in_transaction(tl)                                              \
    (get_segment((tl)->last_associated_segment_num)->running_thread == (tl))


/* Commit Log things */
struct stm_undo_s {
  union {
    struct {
        object_t *object;   /* the object that is modified */
        char *backup;       /* some backup data (a slice of the original obj) */
        uint64_t slice;     /* location and size of this slice (cannot cross
                               pages).  The size is in the lower 2 bytes, and
                               the offset in the remaining 6 bytes. */
    };
    struct {
        intptr_t type;               /* TYPE_POSITION_MARKER */
        uintptr_t marker_odd_number; /* the odd number part of the marker */
        object_t *marker_object;     /* the object part of the marker */
    };
    struct {
        intptr_t type1;             /* TYPE_POSITION_MARKER (again) */
        intptr_t type2;             /* TYPE_MODIFIED_HASHTABLE */
        object_t *modif_hashtable;  /* modified entry is previous stm_undo_s */
    };
  };
};
#define TYPE_POSITION_MARKER    (-1)
#define TYPE_MODIFIED_HASHTABLE (-2)
#define SLICE_OFFSET(slice)  ((slice) >> 16)
#define SLICE_SIZE(slice)    ((int)((slice) & 0xFFFF))
#define NEW_SLICE(offset, size) (((uint64_t)(offset)) << 16 | (size))


/* The model is: we have a global chained list, from 'commit_log_root',
   of 'struct stm_commit_log_entry_s' entries.  Every one is fully
   read-only apart from the 'next' field.  Every one stands for one
   commit that occurred.  It lists the old objects that were modified
   in this commit, and their attached "undo logs" --- that is, the
   data from 'written[n].backup' is the content of (slices of) the
   object as they were *before* that commit occurred.
*/
#define INEV_RUNNING ((void*)-1)
struct stm_commit_log_entry_s {
    struct stm_commit_log_entry_s *volatile next;
    int segment_num;
    uint64_t rev_num;
    size_t written_count;
    struct stm_undo_s written[];
};
static struct stm_commit_log_entry_s commit_log_root;


static void free_bk(struct stm_undo_s *undo);
static struct stm_commit_log_entry_s *malloc_cle(long entries);
static void free_cle(struct stm_commit_log_entry_s *e);


extern char *stm_object_pages;
extern long _stm_segment_nb_pages;
extern int _stm_nb_segments;
extern int _stm_psegment_ofs;
static stm_thread_local_t *stm_all_thread_locals = NULL;


#define REAL_ADDRESS(segment_base, src)   ((segment_base) + (uintptr_t)(src))

#define IS_OVERFLOW_OBJ(pseg, obj) (((obj)->stm_flags & -GCFLAG_OVERFLOW_NUMBER_bit0) \
                                    == (pseg)->overflow_number)

static inline uintptr_t get_index_to_card_index(uintptr_t index) {
    return (index / CARD_SIZE) + 1;
}

static inline uintptr_t get_card_index_to_index(uintptr_t card_index) {
    return (card_index - 1) * CARD_SIZE;
}

static inline struct stm_read_marker_s *get_read_marker(char *segment_base, uintptr_t obj)
{
   return (struct stm_read_marker_s *)(segment_base + (obj >> 4));
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

static inline int get_segment_of_linear_address(char *addr) {
    assert(addr > stm_object_pages && addr < stm_object_pages + TOTAL_MEMORY);
    return (addr - stm_object_pages) / (NB_PAGES * 4096UL);
}

bool obj_should_use_cards(char *seg_base, object_t *obj);

static bool _is_tl_registered(stm_thread_local_t *tl);
static bool _seems_to_be_running_transaction(void);

static void abort_with_mutex(void) __attribute__((noreturn));
static stm_thread_local_t *abort_with_mutex_no_longjmp(void);
static void abort_data_structures_from_segment_num(int segment_num);

static void touch_all_pages_of_obj(object_t *obj, size_t obj_size);

static void synchronize_object_enqueue(object_t *obj);
static void synchronize_objects_flush(void);

static void _signal_handler(int sig, siginfo_t *siginfo, void *context);
static bool _stm_validate(void);
static void _core_commit_transaction(bool external);

static void import_objects(
        int from_segnum,            /* or -1: from undo->backup,
                                       or -2: from undo->backup if not modified */
        uintptr_t pagenum,          /* or -1: "all accessible" */
        struct stm_undo_s *undo,
        struct stm_undo_s *end);


static inline bool was_read_remote(char *base, object_t *obj)
{
    uint8_t other_transaction_read_version =
        ((struct stm_segment_info_s *)REAL_ADDRESS(base, STM_PSEGMENT))
            ->transaction_read_version;
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

static inline void acquire_privatization_lock(int segnum)
{
    stm_spinlock_acquire(get_priv_segment(segnum)->privatization_lock);
}

static inline void release_privatization_lock(int segnum)
{
    stm_spinlock_release(get_priv_segment(segnum)->privatization_lock);
}

static inline bool all_privatization_locks_acquired(void)
{
#ifndef NDEBUG
    long l;
    for (l = 0; l < NB_SEGMENTS; l++) {
        if (!get_priv_segment(l)->privatization_lock)
            return false;
    }
    return true;
#else
    abort();
#endif
}

static inline void acquire_all_privatization_locks(void)
{
    /* XXX: don't do for the sharing seg0 */
    long l;
    for (l = 0; l < NB_SEGMENTS; l++) {
        acquire_privatization_lock(l);
    }
}

static inline void release_all_privatization_locks(void)
{
    long l;
    for (l = NB_SEGMENTS-1; l >= 0; l--) {
        release_privatization_lock(l);
    }
}
