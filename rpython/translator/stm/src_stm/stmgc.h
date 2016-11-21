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

#include "stm/atomic.h"
#include "stm/rewind_setjmp.h"

#if LONG_MAX == 2147483647
# error "Requires a 64-bit environment"
#endif


#ifdef __SEG_GS     /* on a custom patched gcc */
#  define TLPREFIX __seg_gs
#  define _STM_RM_SUFFIX  :8
#elif defined(__clang__)   /* on a clang, hopefully made bug-free */
#  define TLPREFIX __attribute__((address_space(256)))
#  define _STM_RM_SUFFIX  /* nothing */
#else
#  error "needs either a GCC with __seg_gs support, or a bug-freed clang"
#endif

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
    unsigned char rm _STM_RM_SUFFIX;
};

struct stm_segment_info_s {
    unsigned int transaction_read_version;
    int segment_num;
    char *segment_base;
    stm_char *nursery_current;
    stm_char *nursery_mark;
    uintptr_t nursery_end;
    struct stm_thread_local_s *running_thread;
    uint8_t no_safe_point_here;    /* set from outside, triggers an assert */
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
    /* every thread should handle the shadow stack itself */
    struct stm_shadowentry_s *shadowstack, *shadowstack_base;
    /* a generic optional thread-local object */
    object_t *thread_local_obj;
    /* in case this thread runs a transaction that aborts,
       the following raw region of memory is cleared. */
    char *mem_clear_on_abort;
    size_t mem_bytes_to_clear_on_abort;
    /* mechanism to reset a memory location to the value it had at the start
       of the transaction in case of an abort */
    char *mem_reset_on_abort;   /* addr */
    size_t mem_bytes_to_reset_on_abort; /* how many bytes */
    char *mem_stored_for_reset_on_abort; /* content at tx start */
    /* the next fields are handled internally by the library */
    int last_associated_segment_num;   /* always a valid seg num */
    int thread_local_counter;
    int wait_event_emitted;
    struct stm_thread_local_s *prev, *next;
    intptr_t self_or_0_if_atomic;
    void *creating_pthread[2];
} stm_thread_local_t;


/* this should use llvm's coldcc calling convention,
   but it's not exposed to C code so far */
void _stm_write_slowpath(object_t *);
void _stm_write_slowpath_card(object_t *, uintptr_t);
object_t *_stm_allocate_slowpath(ssize_t);
object_t *_stm_allocate_external(ssize_t);

extern volatile intptr_t _stm_detached_inevitable_from_thread;
long _stm_start_transaction(stm_thread_local_t *tl);
void _stm_commit_transaction(void);
void _stm_leave_noninevitable_transactional_zone(void);
#define _stm_detach_inevitable_transaction(tl)  do {                    \
    stm_write_fence();                                                  \
    assert(_stm_detached_inevitable_from_thread == 0);                  \
    if (stmcb_timing_event != NULL && tl->self_or_0_if_atomic != 0)     \
        {stmcb_timing_event(tl, STM_TRANSACTION_DETACH, NULL);}         \
    _stm_detached_inevitable_from_thread = tl->self_or_0_if_atomic;     \
} while (0)
void _stm_reattach_transaction(intptr_t);
void _stm_become_inevitable(const char*);
void _stm_collectable_safe_point(void);

/* for tests, but also used in duhton: */
object_t *_stm_allocate_old(ssize_t size_rounded_up);
char *_stm_real_address(object_t *o);
#ifdef STM_TESTS

#ifdef STM_NO_AUTOMATIC_SETJMP
extern int did_abort;
#endif

#include <stdbool.h>
uint8_t _stm_get_transaction_read_version(void);
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
object_t *_stm_next_last_cl_entry(void);
void _stm_start_enum_last_cl_entry(void);
long _stm_count_cl_entries(void);
long _stm_count_old_objects_with_cards_set(void);
object_t *_stm_enum_old_objects_with_cards_set(long index);
uint64_t _stm_total_allocated(void);
#endif


#ifndef _STM_NURSERY_ZEROED
#define _STM_NURSERY_ZEROED               0
#endif

#define _STM_GCFLAG_WRITE_BARRIER      0x01
#define _STM_GCFLAG_NO_CONFLICT        0x40
#define _STM_FAST_ALLOC           (66*1024)
#define _STM_NSE_SIGNAL_ABORT             1
#define _STM_NSE_SIGNAL_MAX               2

#define _STM_CARD_MARKED 1      /* should always be 1... */
#define _STM_GCFLAG_CARDS_SET          0x8
#define _STM_CARD_BITS                 5   /* must be 5/6/7 for the pypy jit */
#define _STM_CARD_SIZE                 (1 << _STM_CARD_BITS)
#define _STM_MIN_CARD_COUNT            17
#define _STM_MIN_CARD_OBJ_SIZE         (_STM_CARD_SIZE * _STM_MIN_CARD_COUNT)


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
#define STM_NB_SEGMENTS    8

/* Structure of objects
   --------------------

   Objects manipulated by the user program, and managed by this library,
   must start with a "struct object_s" field.  Pointers to any user object
   must use the "TLPREFIX struct foo *" type --- don't forget TLPREFIX.
   The best is to use typedefs like above.

   The object_s part contains some fields reserved for the STM library.
   Right now this is only four bytes.
*/
struct object_s {
    uint32_t stm_flags;            /* reserved for the STM library */
};


/* The read barrier must be called whenever the object 'obj' is read.
   It is not required to call it before reading: it can be delayed for a
   bit, but we must still be in the same "scope": no allocation, no
   transaction commit, nothing that can potentially collect or do a safe
   point (like stm_write() on a different object).  Also, if we might
   have finished the transaction and started the next one, then
   stm_read() needs to be called again.  It can be omitted if
   stm_write() is called, or immediately after getting the object from
   stm_allocate(), as long as the rules above are respected.
*/
__attribute__((always_inline))
static inline void stm_read(object_t *obj)
{
    ((stm_read_marker_t *)(((uintptr_t)obj) >> 4))->rm =
        STM_SEGMENT->transaction_read_version;
}

#define _STM_WRITE_CHECK_SLOWPATH(obj)  \
    UNLIKELY(((obj)->stm_flags & _STM_GCFLAG_WRITE_BARRIER) != 0)

/* The write barrier must be called *before* doing any change to the
   object 'obj'.  If we might have finished the transaction and started
   the next one, then stm_write() needs to be called again.  It is not
   necessary to call it immediately after stm_allocate().
*/
__attribute__((always_inline))
static inline void stm_write(object_t *obj)
{
    if (_STM_WRITE_CHECK_SLOWPATH(obj))
        _stm_write_slowpath(obj);
}

/* The following is a GC-optimized barrier that works on the granularity
   of CARD_SIZE.  It can be used on any array object, but it is only
   useful with those that were internally marked with GCFLAG_HAS_CARDS.
   It has the same purpose as stm_write() for TM and allows write-access
   to a part of an object/array.
   'index' is the array-item-based position within the object, which
   is measured in units returned by stmcb_get_card_base_itemsize().
*/
__attribute__((always_inline))
static inline void stm_write_card(object_t *obj, uintptr_t index)
{
    /* if GCFLAG_WRITE_BARRIER is set, then don't do anything more. */
    if (_STM_WRITE_CHECK_SLOWPATH(obj)) {

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

/* Must be provided by the user of this library.
   The "size rounded up" must be a multiple of 8 and at least 16.
   "Tracing" an object means enumerating all GC references in it,
   by invoking the callback passed as argument.
*/
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




/* Allocate an object of the given size, which must be a multiple
   of 8 and at least 16.  In the fast-path, this is inlined to just
   a few assembler instructions.
*/
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

/* Allocate a weakref object. Weakref objects have a
   reference to an object at the byte-offset
       stmcb_size_rounded_up(obj) - sizeof(void*)
   You must assign the reference before the next collection may happen.
   After that, you must not mutate the reference anymore. However,
   it can become NULL after any GC if the reference dies during that
   collection.
   NOTE: For performance, we assume stmcb_size_rounded_up(weakref)==16
*/
object_t *stm_allocate_weakref(ssize_t size_rounded_up);


/* stm_setup() needs to be called once at the beginning of the program.
   stm_teardown() can be called at the end, but that's not necessary
   and rather meant for tests.
 */
void stm_setup(void);
void stm_teardown(void);

/* The size of each shadow stack, in number of entries.
   Must be big enough to accomodate all STM_PUSH_ROOTs! */
#define STM_SHADOW_STACK_DEPTH   163840

/* Push and pop roots from/to the shadow stack. Only allowed inside
   transaction. */
#define STM_PUSH_ROOT(tl, p)   ((tl).shadowstack++->ss = (object_t *)(p))
#define STM_POP_ROOT(tl, p)    ((p) = (typeof(p))((--(tl).shadowstack)->ss))
#define STM_POP_ROOT_RET(tl)   ((--(tl).shadowstack)->ss)
#define STM_POP_ROOT_DROP(tl)  ((void)(--(tl).shadowstack))

/* Every thread needs to have a corresponding stm_thread_local_t
   structure.  It may be a "__thread" global variable or something else.
   Use the following functions at the start and at the end of a thread.
   The user of this library needs to maintain the two shadowstack fields;
   at any call to stm_allocate(), these fields should point to a range
   of memory that can be walked in order to find the stack roots.
*/
void stm_register_thread_local(stm_thread_local_t *tl);
void stm_unregister_thread_local(stm_thread_local_t *tl);

/* At some key places, like the entry point of the thread and in the
   function with the interpreter's dispatch loop, you need to declare
   a local variable of type 'rewind_jmp_buf' and call these macros.
   IMPORTANT: a function in which you call stm_rewind_jmp_enterframe()
   must never change the value of its own arguments!  If they are
   passed on the stack, gcc can change the value directly there, but
   we're missing the logic to save/restore this part!
*/
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


#ifdef STM_NO_AUTOMATIC_SETJMP
int stm_is_inevitable(stm_thread_local_t *tl);
#else
static inline int stm_is_inevitable(stm_thread_local_t *tl) {
    return !rewind_jmp_armed(&tl->rjthread);
}
#endif


/* Abort the currently running transaction.  This function never
   returns: it jumps back to the start of the transaction (which must
   not be inevitable). */
void stm_abort_transaction(void) __attribute__((noreturn));

/* Turn the current transaction inevitable.
   stm_become_inevitable() itself may still abort the transaction instead
   of returning. */
static inline void stm_become_inevitable(stm_thread_local_t *tl,
                                         const char* msg) {
    assert(STM_SEGMENT->running_thread == tl);
    if (!stm_is_inevitable(tl))
        _stm_become_inevitable(msg);
    /* now, we're running the inevitable transaction, so this var should be 0 */
    assert(_stm_detached_inevitable_from_thread == 0);
}

/* Forces a safe-point if needed.  Normally not needed: this is
   automatic if you call stm_allocate(). */
static inline void stm_safe_point(void) {
    if (STM_SEGMENT->nursery_end <= _STM_NSE_SIGNAL_MAX)
        _stm_collectable_safe_point();
}

/* Forces a collection. */
void stm_collect(long level);


/* A way to detect that we've run for a while and should call
   stm_force_transaction_break() */
static inline int stm_should_break_transaction(void)
{
    return ((intptr_t)STM_SEGMENT->nursery_current >=
            (intptr_t)STM_SEGMENT->nursery_mark);
}
extern uintptr_t stm_fill_mark_nursery_bytes;
/* ^^^ at the start of a transaction, 'nursery_mark' is initialized to
   'stm_fill_mark_nursery_bytes' inside the nursery.  This value can
   be larger than the nursery; every minor collection shifts the
   current 'nursery_mark' down by one nursery-size.  After an abort
   and restart, 'nursery_mark' is set to ~90% of the value it reached
   in the last attempt.
*/

/* "atomic" transaction: a transaction where stm_should_break_transaction()
   always returns false, and where stm_leave_transactional_zone() never
   detach nor terminates the transaction.  (stm_force_transaction_break()
   crashes if called with an atomic transaction.)
*/
uintptr_t stm_is_atomic(stm_thread_local_t *tl);
void stm_enable_atomic(stm_thread_local_t *tl);
void stm_disable_atomic(stm_thread_local_t *tl);


/* Prepare an immortal "prebuilt" object managed by the GC.  Takes a
   pointer to an 'object_t', which should not actually be a GC-managed
   structure but a real static structure.  Returns the equivalent
   GC-managed pointer.  Works by copying it into the GC pages, following
   and fixing all pointers it contains, by doing stm_setup_prebuilt() on
   each of them recursively.  (Note that this will leave garbage in the
   static structure, but it should never be used anyway.) */
object_t *stm_setup_prebuilt(object_t *);
/* The same, if the prebuilt object is actually a weakref. */
object_t *stm_setup_prebuilt_weakref(object_t *);

/* Hash, id.  The id is just the address of the object (of the address
   where it *will* be after the next minor collection).  The hash is the
   same, mangled -- except on prebuilt objects, where it can be
   controlled for each prebuilt object individually.  (Useful uor PyPy) */
long stm_identityhash(object_t *obj);
long stm_id(object_t *obj);
void stm_set_prebuilt_identityhash(object_t *obj, long hash);

/* Returns 1 if the object can still move (it's in the nursery), or 0
   otherwise.  After a minor collection no object can move any more. */
long stm_can_move(object_t *obj);

/* If the current transaction aborts later, invoke 'callback(key)'.  If
   the current transaction commits, then the callback is forgotten.  You
   can only register one callback per key.  You can call
   'stm_call_on_abort(key, NULL)' to cancel an existing callback
   (returns 0 if there was no existing callback to cancel).
   Note: 'key' must be aligned to a multiple of 8 bytes. */
long stm_call_on_abort(stm_thread_local_t *, void *key, void callback(void *));
/* If the current transaction commits later, invoke 'callback(key)'.  If
   the current transaction aborts, then the callback is forgotten.  Same
   restrictions as stm_call_on_abort().  If the transaction is or becomes
   inevitable, 'callback(key)' is called immediately. */
long stm_call_on_commit(stm_thread_local_t *, void *key, void callback(void *));


/* Similar to stm_become_inevitable(), but additionally suspend all
   other threads.  A very heavy-handed way to make sure that no other
   transaction is running concurrently.  Avoid as much as possible.
   Other transactions will continue running only after this transaction
   commits.  (deprecated, not working any more according to demo_random2) */
//void stm_become_globally_unique_transaction(stm_thread_local_t *tl, const char *msg);

/* Moves the transaction forward in time by validating the read and
   write set with all commits that happened since the last validation
   (explicit or implicit). */
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

    /* DETACH/REATTACH is used for leaving/reentering the transactional */
    STM_TRANSACTION_DETACH,
    STM_TRANSACTION_REATTACH,

    /* inevitable contention: all threads that try to become inevitable
       have a STM_BECOME_INEVITABLE event with a position marker.  Then,
       if it waits it gets a STM_WAIT_OTHER_INEVITABLE.  It is possible
       that a thread gets STM_BECOME_INEVITABLE followed by
       STM_TRANSACTION_ABORT if it fails to become inevitable. */
    STM_BECOME_INEVITABLE,

    /* write-read contention: a "marker" is included in the PYPYSTM file
       saying where the write was done.  Followed by STM_TRANSACTION_ABORT. */
    STM_CONTENTION_WRITE_READ,

    /* always one STM_WAIT_xxx followed later by STM_WAIT_DONE or
       possibly STM_TRANSACTION_ABORT */
    STM_WAIT_FREE_SEGMENT,
    STM_WAIT_SYNCING,
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
    uintptr_t odd_number;  /* marker odd number, or 0 if marker is missing */
    object_t *object;      /* marker object, or NULL if marker is missing */
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
    STM_POP_ROOT_DROP(tl);                      \
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



/* Entering and leaving a "transactional code zone": a (typically very
   large) section in the code where we are running a transaction.
   This is the STM equivalent to "acquire the GIL" and "release the
   GIL", respectively.  stm_read(), stm_write(), stm_allocate(), and
   other functions should only be called from within a transaction.

   Note that transactions, in the STM sense, cover _at least_ one
   transactional code zone.  They may be longer; for example, if one
   thread does a lot of stm_enter_transactional_zone() +
   stm_become_inevitable() + stm_leave_transactional_zone(), as is
   typical in a thread that does a lot of C function calls, then we
   get only a few bigger inevitable transactions that cover the many
   short transactional zones.  This is done by having
   stm_leave_transactional_zone() turn the current transaction
   inevitable and detach it from the running thread (if there is no
   other inevitable transaction running so far).  Then
   stm_enter_transactional_zone() will try to reattach to it.  This is
   far more efficient than constantly starting and committing
   transactions.

   stm_enter_transactional_zone() and stm_leave_transactional_zone()
   preserve the value of errno.
*/
#ifdef STM_DEBUGPRINT
#include <stdio.h>
#endif
static inline void stm_enter_transactional_zone(stm_thread_local_t *tl) {
    intptr_t self = tl->self_or_0_if_atomic;
    if (__sync_bool_compare_and_swap(&_stm_detached_inevitable_from_thread,
                                     self, 0)) {
        if (self != 0 && stmcb_timing_event != NULL) {
            /* for atomic transactions, we don't emit DETACH/REATTACH */
            stmcb_timing_event(tl, STM_TRANSACTION_REATTACH, NULL);
        }
#ifdef STM_DEBUGPRINT
        fprintf(stderr, "stm_enter_transactional_zone fast path\n");
#endif
    }
    else {
        _stm_reattach_transaction(self);
        /* _stm_detached_inevitable_from_thread should be 0 here, but
           it can already have been changed from a parallel thread
           (assuming we're not inevitable ourselves) */
    }
}
static inline void stm_leave_transactional_zone(stm_thread_local_t *tl) {
    assert(STM_SEGMENT->running_thread == tl);
    if (stm_is_inevitable(tl)) {
#ifdef STM_DEBUGPRINT
        fprintf(stderr, "stm_leave_transactional_zone fast path\n");
#endif
        _stm_detach_inevitable_transaction(tl);
    }
    else {
        _stm_leave_noninevitable_transactional_zone();
    }
}

/* stm_force_transaction_break() is in theory equivalent to
   stm_leave_transactional_zone() immediately followed by
   stm_enter_transactional_zone(); however, it is supposed to be
   called in CPU-heavy threads that had a transaction run for a while,
   and so it *always* forces a commit and starts the next transaction.
   The new transaction is never inevitable.  See also
   stm_should_break_transaction(). */
void stm_force_transaction_break(stm_thread_local_t *tl);


/* Support for destructors.  This is a simple version of
   finalizers that guarantees not to do anything fancy, like not
   resurrecting objects. */
extern void (*stmcb_destructor)(object_t *);
void stm_enable_destructor(object_t *);

/* XXX: Support for regular finalizers.  Unreachable objects with
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
typedef void (*stm_finalizer_trigger_fn)(void);
void (*stmcb_finalizer)(object_t *);
void stm_setup_finalizer_queues(int number, stm_finalizer_trigger_fn *triggers);
void stm_enable_finalizer(int queue_index, object_t *obj);

/* Returns the next object that supposedly died and should have its finalizer
   called. XXX: This function turns the transaction inevitable. */
object_t *stm_next_to_finalize(int queue_index);


/* dummies for now: */
static inline void stm_flush_timing(stm_thread_local_t *tl, int verbose) {}


/* Hashtables.  Keys are 64-bit unsigned integers, values are
   'object_t *'.  Note that the type 'stm_hashtable_t' is not an
   object type at all; you need to allocate and free it explicitly.
   If you want to embed the hashtable inside an 'object_t' you
   probably need a destructor to do the freeing. */
typedef struct stm_hashtable_s stm_hashtable_t;
typedef TLPREFIX struct stm_hashtable_entry_s stm_hashtable_entry_t;

stm_hashtable_t *stm_hashtable_create(void);
void stm_hashtable_free(stm_hashtable_t *);
/* lookup returns a reference to an entry. This entry is only valid
   in the current transaction and needs to be looked up again if there
   may have been a break inbetween. */
stm_hashtable_entry_t *stm_hashtable_lookup(object_t *, stm_hashtable_t *,
                                            uintptr_t key);
object_t *stm_hashtable_read(object_t *, stm_hashtable_t *, uintptr_t key);
void stm_hashtable_write(object_t *, stm_hashtable_t *, uintptr_t key,
                         object_t *nvalue, stm_thread_local_t *);
void stm_hashtable_write_entry(object_t *hobj, stm_hashtable_entry_t *entry,
                               object_t *nvalue);
long stm_hashtable_length_upper_bound(stm_hashtable_t *);
stm_hashtable_entry_t *stm_hashtable_pickitem(object_t *, stm_hashtable_t *);

/* WARNING: stm_hashtable_list does not do a stm_write() on the 'results'
   argument. 'results' may point inside an object. So if 'results' may be
   a part of an old obj (which may have survived a minor GC), then make
   sure to call stm_write() on the obj before calling this function. */
long stm_hashtable_list(object_t *, stm_hashtable_t *,
                        stm_hashtable_entry_t * TLPREFIX *results);
extern uint32_t stm_hashtable_entry_userdata;
void stm_hashtable_tracefn(struct object_s *, stm_hashtable_t *,
                           void (object_t **));

struct stm_hashtable_entry_s {
    struct object_s header;
    uint32_t userdata;
    uintptr_t index;
    object_t *object;
};

/* Hashtable iterators.  You get a raw 'table' pointer when you make
   an iterator, which you pass to stm_hashtable_iter_next().  This may
   or may not return items added after stm_hashtable_iter() was
   called; there is no logic so far to detect changes (unlike Python's
   RuntimeError).  When the GC traces, you must keep the table pointer
   alive with stm_hashtable_iter_tracefn().  The original hashtable
   object must also be kept alive. */
typedef struct stm_hashtable_table_s stm_hashtable_table_t;
stm_hashtable_table_t *stm_hashtable_iter(stm_hashtable_t *);
stm_hashtable_entry_t **
stm_hashtable_iter_next(object_t *hobj, stm_hashtable_table_t *table,
                        stm_hashtable_entry_t **previous);
void stm_hashtable_iter_tracefn(stm_hashtable_table_t *table,
                                void trace(object_t **));


/* Queues.  The items you put() and get() back are in random order.
   Like hashtables, the type 'stm_queue_t' is not an object type at
   all; you need to allocate and free it explicitly.  If you want to
   embed the queue inside an 'object_t' you probably need a destructor
   to do the freeing. */
typedef struct stm_queue_s stm_queue_t;

stm_queue_t *stm_queue_create(void);
void stm_queue_free(stm_queue_t *);
/* put() does not cause delays or transaction breaks */
void stm_queue_put(object_t *qobj, stm_queue_t *queue, object_t *newitem);
/* get() can commit and wait outside a transaction (so push roots).
   Unsuitable if the current transaction is atomic!  With timeout < 0.0,
   waits forever; with timeout >= 0.0, returns NULL in an *inevitable*
   transaction (this is needed to ensure correctness). */
object_t *stm_queue_get(object_t *qobj, stm_queue_t *queue, double timeout,
                        stm_thread_local_t *tl);
/* task_done() and join(): see https://docs.python.org/2/library/queue.html */
void stm_queue_task_done(stm_queue_t *queue);
/* join() commits and waits outside a transaction (so push roots).
   Unsuitable if the current transaction is atomic! */
long stm_queue_join(object_t *qobj, stm_queue_t *queue, stm_thread_local_t *tl);
void stm_queue_tracefn(stm_queue_t *queue, void trace(object_t **));



/* stm_allocate_noconflict() allocates a special kind of object. Validation
   will never detect conflicts on such an object. However, writes to it can
   get lost. More precisely: every possible point for validation during a
   transaction may import a committed version of such objs, thereby resetting
   it or even contain not-yet-seen values from other (committed) transactions.
   Hence, changes to such an obj that a transaction commits may or may not
   propagate to other transactions. */
__attribute__((always_inline))
static inline object_t *stm_allocate_noconflict(ssize_t size_rounded_up)
{
    object_t *o = stm_allocate(size_rounded_up);
    o->stm_flags |= _STM_GCFLAG_NO_CONFLICT;
    return o;
}



/* ==================== END ==================== */

extern void (*stmcb_expand_marker)(char *segment_base, uintptr_t odd_number,
                            object_t *following_object,
                            char *outputbuf, size_t outputbufsize);

extern void (*stmcb_debug_print)(const char *cause, double time,
                          const char *marker);

#endif
