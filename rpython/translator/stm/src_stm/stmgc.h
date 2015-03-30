/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STMGC_H
#define _STMGC_H

/* ==================== INTERNAL ==================== */

/* See "API" below. */


#include <stddef.h>
#include <stdint.h>
#include <assert.h>
#include <limits.h>
#include <unistd.h>

#include "stm/rewind_setjmp.h"

#if LONG_MAX == 2147483647
# error "Requires a 64-bit environment"
#endif


#define TLPREFIX __attribute__((address_space(256)))

typedef TLPREFIX struct object_s object_t;
typedef TLPREFIX struct stm_segment_info_s stm_segment_info_t;
typedef TLPREFIX struct stm_read_marker_s stm_read_marker_t;
typedef TLPREFIX char stm_char;

struct stm_read_marker_s {
    /* In every segment, every object has a corresponding read marker.
       We assume that objects are at least 16 bytes long, and use
       their address divided by 16.  The read marker is equal to
       'STM_SEGMENT->transaction_read_version' if and only if the
       object was read in the current transaction.  The nurseries
       also have corresponding read markers, but they are never used. */
    uint8_t rm;
};

struct stm_segment_info_s {
    uint8_t transaction_read_version;
    int segment_num;
    char *segment_base;
    stm_char *nursery_current;
    uintptr_t nursery_end;
    struct stm_thread_local_s *running_thread;
};
#define STM_SEGMENT           ((stm_segment_info_t *)4352)


struct stm_shadowentry_s {
    /* Like stm_read_marker_s, this is a struct to enable better
       aliasing analysis in the C code. */
    object_t *ss;
};

typedef struct stm_thread_local_s {
    /* rewind_setjmp's interface */
    rewind_jmp_thread rjthread;
    struct stm_shadowentry_s *shadowstack, *shadowstack_base;

    /* a generic optional thread-local object */
    object_t *thread_local_obj;

    char *mem_clear_on_abort;
    size_t mem_bytes_to_clear_on_abort;
    long last_abort__bytes_in_nursery;
    /* the next fields are handled internally by the library */
    int associated_segment_num;
    int last_associated_segment_num;
    int thread_local_counter;
    struct stm_thread_local_s *prev, *next;
    void *creating_pthread[2];
} stm_thread_local_t;

#ifndef _STM_NURSERY_ZEROED
#define _STM_NURSERY_ZEROED               0
#endif

#define _STM_GCFLAG_WRITE_BARRIER      0x01
#define _STM_FAST_ALLOC           (66*1024)
#define _STM_NSE_SIGNAL_ABORT             1
#define _STM_NSE_SIGNAL_MAX               2

#define _STM_CARD_MARKED 1      /* should always be 1... */
#define _STM_GCFLAG_CARDS_SET          0x8
#define _STM_CARD_BITS                 5   /* must be 5/6/7 for the pypy jit */
#define _STM_CARD_SIZE                 (1 << _STM_CARD_BITS)
#define _STM_MIN_CARD_COUNT            17
#define _STM_MIN_CARD_OBJ_SIZE         (_STM_CARD_SIZE * _STM_MIN_CARD_COUNT)

void _stm_write_slowpath(object_t *);
void _stm_write_slowpath_card(object_t *, uintptr_t);
object_t *_stm_allocate_slowpath(ssize_t);
object_t *_stm_allocate_external(ssize_t);
void _stm_become_inevitable(const char*);
void _stm_collectable_safe_point();

object_t *_stm_allocate_old(ssize_t size_rounded_up);
char *_stm_real_address(object_t *o);
#ifdef STM_TESTS
#include <stdbool.h>
uint8_t _stm_get_transaction_read_version();
uint8_t _stm_get_card_value(object_t *obj, long idx);
bool _stm_was_read(object_t *obj);
bool _stm_was_written(object_t *obj);
bool _stm_was_written_card(object_t *obj);
bool _stm_is_accessible_page(uintptr_t pagenum);

void _stm_test_switch(stm_thread_local_t *tl);
void _stm_test_switch_segment(int segnum);
void _push_obj_to_other_segments(object_t *obj);

void _stm_largemalloc_init_arena(char *data_start, size_t data_size);
int _stm_largemalloc_resize_arena(size_t new_size);
char *_stm_largemalloc_data_start(void);
char *_stm_large_malloc(size_t request_size);
void _stm_large_free(char *data);
void _stm_large_dump(void);
bool (*_stm_largemalloc_keep)(char *data);
void _stm_largemalloc_sweep(void);


char *stm_object_pages;
char *stm_file_pages;
object_t *_stm_allocate_old_small(ssize_t size_rounded_up);
bool (*_stm_smallmalloc_keep)(char *data);
void _stm_smallmalloc_sweep_test(void);

void _stm_start_safe_point(void);
void _stm_stop_safe_point(void);

char *_stm_get_segment_base(long index);
bool _stm_in_transaction(stm_thread_local_t *tl);
void _stm_set_nursery_free_count(uint64_t free_count);
long _stm_count_modified_old_objects(void);
long _stm_count_objects_pointing_to_nursery(void);
object_t *_stm_enum_modified_old_objects(long index);
object_t *_stm_enum_objects_pointing_to_nursery(long index);
object_t *_stm_next_last_cl_entry();
void _stm_start_enum_last_cl_entry();
long _stm_count_cl_entries();
long _stm_count_old_objects_with_cards_set(void);
object_t *_stm_enum_old_objects_with_cards_set(long index);
uint64_t _stm_total_allocated(void);
#endif

/* ==================== HELPERS ==================== */
#ifdef NDEBUG
#define OPT_ASSERT(cond) do { if (!(cond)) __builtin_unreachable(); } while (0)
#else
#define OPT_ASSERT(cond) assert(cond)
#endif
#define LIKELY(x)   __builtin_expect(x, 1)
#define UNLIKELY(x) __builtin_expect(x, 0)
#define IMPLY(a, b) (!(a) || (b))


/* ==================== PUBLIC API ==================== */

/* Number of segments (i.e. how many transactions can be executed in
   parallel, in maximum).  If you try to start transactions in more
   threads than the number of segments, it will block, waiting for the
   next segment to become free.
*/
#define STM_NB_SEGMENTS    4


struct object_s {
    uint32_t stm_flags;            /* reserved for the STM library */
};

extern ssize_t stmcb_size_rounded_up(struct object_s *);
void stmcb_trace(struct object_s *obj, void visit(object_t **));
/* a special trace-callback that is only called for the marked
   ranges of indices (using stm_write_card(o, index)) */
extern void stmcb_trace_cards(struct object_s *, void (object_t **),
                              uintptr_t start, uintptr_t stop);
/* this function will be called on objects that support cards.
   It returns the base_offset (in bytes) inside the object from
   where the indices start, and item_size (in bytes) for the size of
   one item */
extern void stmcb_get_card_base_itemsize(struct object_s *,
                                         uintptr_t offset_itemsize[2]);
/* returns whether this object supports cards. we will only call
   stmcb_get_card_base_itemsize on objs that do so. */
extern long stmcb_obj_supports_cards(struct object_s *);




__attribute__((always_inline))
static inline void stm_read(object_t *obj)
{
    ((stm_read_marker_t *)(((uintptr_t)obj) >> 4))->rm =
        STM_SEGMENT->transaction_read_version;
}

__attribute__((always_inline))
static inline void stm_write(object_t *obj)
{
    if (UNLIKELY((obj->stm_flags & _STM_GCFLAG_WRITE_BARRIER) != 0))
        _stm_write_slowpath(obj);
}


__attribute__((always_inline))
static inline void stm_write_card(object_t *obj, uintptr_t index)
{
    /* if GCFLAG_WRITE_BARRIER is set, then don't do anything more. */
    if (UNLIKELY((obj->stm_flags & _STM_GCFLAG_WRITE_BARRIER) != 0)) {

        /* GCFLAG_WRITE_BARRIER is not set.  This might be because
           it's the first time we see a given small array; or it might
           be because it's a big array with card marking.  In the
           latter case we will always reach this point, even if we
           already marked the correct card.  Based on the idea that it
           is actually the most common case, check it here.  If the
           array doesn't actually use card marking, the following read
           is a bit nonsensical, but in a way that should never return
           CARD_MARKED by mistake.

           The computation of the card marker is further optimized by
           assuming that large objects are allocated to multiples of
           16 (rather than just 8, as all objects are).  Under this
           assumption the following code is equivalent to:

               (obj >> 4) + (index / _STM_CARD_SIZE) + 1

           The code below however takes only a couple of assembler
           instructions.  It also assumes that the intermediate value
           fits in a 64-bit value, which it clearly does (all values
           are much smaller than 2 ** 60).
        */
        uintptr_t v = (((uintptr_t)obj) << (_STM_CARD_BITS - 4)) + index;
        stm_read_marker_t *card1 = (stm_read_marker_t *)(v >> _STM_CARD_BITS);
        if (card1[1].rm != _STM_CARD_MARKED) {

            /* slow path. */
            _stm_write_slowpath_card(obj, index);
        }
    }
}


__attribute__((always_inline))
static inline object_t *stm_allocate(ssize_t size_rounded_up)
{
    OPT_ASSERT(size_rounded_up >= 16);
    OPT_ASSERT((size_rounded_up & 7) == 0);

    if (UNLIKELY(size_rounded_up >= _STM_FAST_ALLOC))
        return _stm_allocate_external(size_rounded_up);

    stm_char *p = STM_SEGMENT->nursery_current;
    stm_char *end = p + size_rounded_up;
    STM_SEGMENT->nursery_current = end;
    if (UNLIKELY((uintptr_t)end > STM_SEGMENT->nursery_end))
        return _stm_allocate_slowpath(size_rounded_up);

#if !_STM_NURSERY_ZEROED
    ((object_t *)p)->stm_flags = 0;
#endif
    return (object_t *)p;
}


object_t *stm_allocate_weakref(ssize_t size_rounded_up);


void stm_setup(void);
void stm_teardown(void);

#define STM_SHADOW_STACK_DEPTH   163840
#define STM_PUSH_ROOT(tl, p)   ((tl).shadowstack++->ss = (object_t *)(p))
#define STM_POP_ROOT(tl, p)    ((p) = (typeof(p))((--(tl).shadowstack)->ss))
#define STM_POP_ROOT_RET(tl)   ((--(tl).shadowstack)->ss)

void stm_register_thread_local(stm_thread_local_t *tl);
void stm_unregister_thread_local(stm_thread_local_t *tl);

#define stm_rewind_jmp_enterprepframe(tl, rjbuf)                        \
    rewind_jmp_enterprepframe(&(tl)->rjthread, rjbuf, (tl)->shadowstack)
#define stm_rewind_jmp_enterframe(tl, rjbuf)       \
    rewind_jmp_enterframe(&(tl)->rjthread, rjbuf, (tl)->shadowstack)
#define stm_rewind_jmp_leaveframe(tl, rjbuf)       \
    rewind_jmp_leaveframe(&(tl)->rjthread, rjbuf, (tl)->shadowstack)
#define stm_rewind_jmp_setjmp(tl)                  \
    rewind_jmp_setjmp(&(tl)->rjthread, (tl)->shadowstack)
#define stm_rewind_jmp_longjmp(tl)                 \
    rewind_jmp_longjmp(&(tl)->rjthread)
#define stm_rewind_jmp_forget(tl)                  \
    rewind_jmp_forget(&(tl)->rjthread)
#define stm_rewind_jmp_restore_shadowstack(tl)  do {     \
    assert(rewind_jmp_armed(&(tl)->rjthread));           \
    (tl)->shadowstack = (struct stm_shadowentry_s *)     \
        rewind_jmp_restore_shadowstack(&(tl)->rjthread); \
} while (0)
#define stm_rewind_jmp_enum_shadowstack(tl, callback)    \
    rewind_jmp_enum_shadowstack(&(tl)->rjthread, callback)


long stm_start_transaction(stm_thread_local_t *tl);
void stm_start_inevitable_transaction(stm_thread_local_t *tl);

void stm_commit_transaction(void);

/* Temporary fix?  Call this outside a transaction.  If there is an
   inevitable transaction running somewhere else, wait until it finishes. */
void stm_wait_for_current_inevitable_transaction(void);

void stm_abort_transaction(void) __attribute__((noreturn));

void stm_collect(long level);

long stm_identityhash(object_t *obj);
long stm_id(object_t *obj);
void stm_set_prebuilt_identityhash(object_t *obj, long hash);

long stm_can_move(object_t *obj);

object_t *stm_setup_prebuilt(object_t *);
object_t *stm_setup_prebuilt_weakref(object_t *);

long stm_call_on_abort(stm_thread_local_t *, void *key, void callback(void *));
long stm_call_on_commit(stm_thread_local_t *, void *key, void callback(void *));

static inline void stm_safe_point(void) {
    if (STM_SEGMENT->nursery_end <= _STM_NSE_SIGNAL_MAX)
        _stm_collectable_safe_point();
}


#ifdef STM_NO_AUTOMATIC_SETJMP
int stm_is_inevitable(void);
#else
static inline int stm_is_inevitable(void) {
    return !rewind_jmp_armed(&STM_SEGMENT->running_thread->rjthread);
}
#endif
static inline void stm_become_inevitable(stm_thread_local_t *tl,
                                         const char* msg) {
    assert(STM_SEGMENT->running_thread == tl);
    if (!stm_is_inevitable())
        _stm_become_inevitable(msg);
}

void stm_become_globally_unique_transaction(stm_thread_local_t *tl, const char *msg);
void stm_validate(void);

/* Temporarily stop all the other threads, by waiting until they
   reach a safe-point.  Don't nest the calls to stop/resume and make sure
   that resume is called.  The current transaction is turned inevitable. */
void stm_stop_all_other_threads(void);
void stm_resume_all_other_threads(void);


/* Profiling events.  In the comments: content of the markers, if any */
enum stm_event_e {
    /* always STM_TRANSACTION_START followed later by one of COMMIT or ABORT */
    STM_TRANSACTION_START,
    STM_TRANSACTION_COMMIT,
    STM_TRANSACTION_ABORT,

    /* write-read contention: a "marker" is included in the PYPYSTM file
       saying where the write was done.  Followed by STM_TRANSACTION_ABORT. */
    STM_CONTENTION_WRITE_READ,

    /* inevitable contention: all threads that try to become inevitable
       have a STM_BECOME_INEVITABLE event with a position marker.  Then,
       if it waits it gets a STM_WAIT_OTHER_INEVITABLE.  It is possible
       that a thread gets STM_BECOME_INEVITABLE followed by
       STM_TRANSACTION_ABORT if it fails to become inevitable. */
    STM_BECOME_INEVITABLE,

    /* always one STM_WAIT_xxx followed later by STM_WAIT_DONE */
    STM_WAIT_FREE_SEGMENT,
    STM_WAIT_SYNC_PAUSE,
    STM_WAIT_OTHER_INEVITABLE,
    STM_WAIT_DONE,

    /* start and end of GC cycles */
    STM_GC_MINOR_START,
    STM_GC_MINOR_DONE,
    STM_GC_MAJOR_START,
    STM_GC_MAJOR_DONE,

    _STM_EVENT_N
};

#define STM_EVENT_NAMES                         \
    "transaction start",                        \
    "transaction commit",                       \
    "transaction abort",                        \
    "contention write read",                    \
    "wait free segment",                        \
    "wait other inevitable",                    \
    "wait done",                                \
    "gc minor start",                           \
    "gc minor done",                            \
    "gc major start",                           \
    "gc major done"

/* The markers pushed in the shadowstack are an odd number followed by a
   regular object pointer. */
typedef struct {
    uintptr_t odd_number;
    object_t *object;
} stm_loc_marker_t;
extern void (*stmcb_timing_event)(stm_thread_local_t *tl, /* the local thread */
                                  enum stm_event_e event,
                                  stm_loc_marker_t *marker);

/* Calling this sets up a stmcb_timing_event callback that will produce
   a binary file called 'profiling_file_name'.  Call it with
   'fork_mode == 0' for only the main process, and with
   'fork_mode == 1' to also write files called
   'profiling_file_name.fork<PID>' after a fork().  Call it with NULL to
   stop profiling.  Returns -1 in case of error (see errno then).
   The optional 'expand_marker' function pointer is called to expand
   the marker's odd_number and object into printable data, starting at
   the given position and with the given maximum length. */
typedef int (*stm_expand_marker_fn)(char *seg_base, stm_loc_marker_t *marker,
                                    char *output, int output_size);
int stm_set_timing_log(const char *profiling_file_name, int fork_mode,
                       stm_expand_marker_fn expand_marker);


/* Convenience macros to push the markers into the shadowstack */
#define STM_PUSH_MARKER(tl, odd_num, p)   do {  \
    uintptr_t _odd_num = (odd_num);             \
    assert(_odd_num & 1);                       \
    STM_PUSH_ROOT(tl, _odd_num);                \
    STM_PUSH_ROOT(tl, p);                       \
} while (0)

#define STM_POP_MARKER(tl)   ({                 \
    object_t *_popped = STM_POP_ROOT_RET(tl);   \
    STM_POP_ROOT_RET(tl);                       \
    _popped;                                    \
})

#define STM_UPDATE_MARKER_NUM(tl, odd_num)  do {                \
    uintptr_t _odd_num = (odd_num);                             \
    assert(_odd_num & 1);                                       \
    struct stm_shadowentry_s *_ss = (tl).shadowstack - 2;       \
    while (!(((uintptr_t)(_ss->ss)) & 1)) {                     \
        _ss--;                                                  \
        assert(_ss >= (tl).shadowstack_base);                   \
    }                                                           \
    _ss->ss = (object_t *)_odd_num;                             \
} while (0)


/* Support for light finalizers.  This is a simple version of
   finalizers that guarantees not to do anything fancy, like not
   resurrecting objects. */
extern void (*stmcb_light_finalizer)(object_t *);
void stm_enable_light_finalizer(object_t *);

/* Support for regular finalizers.  Unreachable objects with
   finalizers are kept alive, as well as everything they point to, and
   stmcb_finalizer() is called after the major GC.  If there are
   several objects with finalizers that reference each other in a
   well-defined order (i.e. there are no cycles), then they are
   finalized in order from outermost to innermost (i.e. starting with
   the ones that are unreachable even from others).

   For objects that have been created by the current transaction, if a
   major GC runs while that transaction is alive and finds the object
   unreachable, the finalizer is called immediately in the same
   transaction.  For older objects, the finalizer is called from a
   random thread between regular transactions, in a new custom
   transaction. */
extern void (*stmcb_finalizer)(object_t *);
object_t *stm_allocate_with_finalizer(ssize_t size_rounded_up);


/* dummies for now: */
static inline void stm_flush_timing(stm_thread_local_t *tl, int verbose) {}

/* ==================== END ==================== */

static void (*stmcb_expand_marker)(char *segment_base, uintptr_t odd_number,
                            object_t *following_object,
                            char *outputbuf, size_t outputbufsize);

static void (*stmcb_debug_print)(const char *cause, double time,
                          const char *marker);

#endif
