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
typedef TLPREFIX struct stm_creation_marker_s stm_creation_marker_t;
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

enum stm_time_e {
    STM_TIME_OUTSIDE_TRANSACTION,
    STM_TIME_RUN_CURRENT,
    STM_TIME_RUN_COMMITTED,
    STM_TIME_RUN_ABORTED_WRITE_WRITE,
    STM_TIME_RUN_ABORTED_WRITE_READ,
    STM_TIME_RUN_ABORTED_INEVITABLE,
    STM_TIME_RUN_ABORTED_OTHER,
    STM_TIME_WAIT_FREE_SEGMENT,
    STM_TIME_WAIT_WRITE_READ,
    STM_TIME_WAIT_INEVITABLE,
    STM_TIME_WAIT_OTHER,
    STM_TIME_SYNC_COMMIT_SOON,
    STM_TIME_BOOKKEEPING,
    STM_TIME_MINOR_GC,
    STM_TIME_MAJOR_GC,
    STM_TIME_SYNC_PAUSE,
    _STM_TIME_N
};

#define _STM_MARKER_LEN  80

typedef struct stm_thread_local_s {
    /* every thread should handle the shadow stack itself */
    struct stm_shadowentry_s *shadowstack, *shadowstack_base;
    /* rewind_setjmp's interface */
    rewind_jmp_thread rjthread;
    /* a generic optional thread-local object */
    object_t *thread_local_obj;
    /* in case this thread runs a transaction that aborts,
       the following raw region of memory is cleared. */
    char *mem_clear_on_abort;
    size_t mem_bytes_to_clear_on_abort;
    /* after an abort, some details about the abort are stored there.
       (these fields are not modified on a successful commit) */
    long last_abort__bytes_in_nursery;
    /* timing information, accumulated */
    uint32_t events[_STM_TIME_N];
    float timing[_STM_TIME_N];
    double _timing_cur_start;
    enum stm_time_e _timing_cur_state;
    /* the marker with the longest associated time so far */
    enum stm_time_e longest_marker_state;
    double longest_marker_time;
    char longest_marker_self[_STM_MARKER_LEN];
    char longest_marker_other[_STM_MARKER_LEN];
    /* the next fields are handled internally by the library */
    int associated_segment_num;
    struct stm_thread_local_s *prev, *next;
    void *creating_pthread[2];
} stm_thread_local_t;

/* this should use llvm's coldcc calling convention,
   but it's not exposed to C code so far */
void _stm_write_slowpath(object_t *);
void _stm_write_slowpath_card(object_t *, uintptr_t);
char _stm_write_slowpath_card_extra(object_t *);
long _stm_write_slowpath_card_extra_base(void);
#define _STM_CARD_MARKED 100
object_t *_stm_allocate_slowpath(ssize_t);
object_t *_stm_allocate_external(ssize_t);
void _stm_become_inevitable(const char*);
void _stm_collectable_safe_point(void);

/* for tests, but also used in duhton: */
object_t *_stm_allocate_old(ssize_t size_rounded_up);
char *_stm_real_address(object_t *o);
#ifdef STM_TESTS
#include <stdbool.h>
bool _stm_was_read(object_t *obj);
bool _stm_was_written(object_t *obj);
bool _stm_was_written_card(object_t *obj);
uintptr_t _stm_get_private_page(uintptr_t pagenum);
bool _stm_in_transaction(stm_thread_local_t *tl);
char *_stm_get_segment_base(long index);
void _stm_test_switch(stm_thread_local_t *tl);
void _stm_largemalloc_init_arena(char *data_start, size_t data_size);
int _stm_largemalloc_resize_arena(size_t new_size);
char *_stm_largemalloc_data_start(void);
char *_stm_large_malloc(size_t request_size);
void _stm_large_free(char *data);
void _stm_large_dump(void);
bool (*_stm_largemalloc_keep)(char *data);
void _stm_largemalloc_sweep(void);
void _stm_start_safe_point(void);
void _stm_stop_safe_point(void);
void _stm_set_nursery_free_count(uint64_t free_count);
long _stm_count_modified_old_objects(void);
long _stm_count_objects_pointing_to_nursery(void);
long _stm_count_old_objects_with_cards(void);
object_t *_stm_enum_modified_old_objects(long index);
object_t *_stm_enum_objects_pointing_to_nursery(long index);
object_t *_stm_enum_old_objects_with_cards(long index);
uint64_t _stm_total_allocated(void);
#endif

#define _STM_GCFLAG_WRITE_BARRIER      0x01
#define _STM_GCFLAG_CARDS_SET          0x08
#define _STM_CARD_SIZE                 32     /* must be >= 32 */
#define _STM_MIN_CARD_COUNT            17
#define _STM_MIN_CARD_OBJ_SIZE         (_STM_CARD_SIZE * _STM_MIN_CARD_COUNT)
#define _STM_NSE_SIGNAL_MAX     _STM_TIME_N
#define _STM_FAST_ALLOC           (66*1024)


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


/* Structure of objects
   --------------------

   Objects manipulated by the user program, and managed by this library,
   must start with a "struct object_s" field.  Pointers to any user object
   must use the "TLPREFIX struct foo *" type --- don't forget TLPREFIX.
   The best is to use typedefs like above.

   The object_s part contains some fields reserved for the STM library.
   Right now this is only one byte.
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

/* The write barrier must be called *before* doing any change to the
   object 'obj'.  If we might have finished the transaction and started
   the next one, then stm_write() needs to be called again.  It is not
   necessary to call it immediately after stm_allocate().
*/
__attribute__((always_inline))
static inline void stm_write(object_t *obj)
{
    if (UNLIKELY((obj->stm_flags & _STM_GCFLAG_WRITE_BARRIER) != 0))
        _stm_write_slowpath(obj);
}

/* The following is a GC-optimized barrier that works on the granularity
   of CARD_SIZE.  It can be used on any array object, but it is only
   useful with those that were internally marked with GCFLAG_HAS_CARDS.
   It has the same purpose as stm_write() for TM.
   'index' is the array-item-based position within the object, which
   is measured in units returned by stmcb_get_card_base_itemsize().
*/
__attribute__((always_inline))
static inline void stm_write_card(object_t *obj, uintptr_t index)
{
    if (UNLIKELY((obj->stm_flags & _STM_GCFLAG_WRITE_BARRIER) != 0))
        _stm_write_slowpath_card(obj, index);
}

/* Must be provided by the user of this library.
   The "size rounded up" must be a multiple of 8 and at least 16.
   "Tracing" an object means enumerating all GC references in it,
   by invoking the callback passed as argument.
   stmcb_commit_soon() is called when it is advised to commit
   the transaction as soon as possible in order to avoid conflicts
   or improve performance in general.
*/
extern ssize_t stmcb_size_rounded_up(struct object_s *);
extern void stmcb_trace(struct object_s *, void (object_t **));
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
extern void stmcb_commit_soon(void);


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
   a local variable of type 'rewind_jmp_buf' and call these macros. */
#define stm_rewind_jmp_enterprepframe(tl, rjbuf)   \
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

/* Starting and ending transactions.  stm_read(), stm_write() and
   stm_allocate() should only be called from within a transaction.
   The stm_start_transaction() call returns the number of times it
   returned, starting at 0.  If it is > 0, then the transaction was
   aborted and restarted this number of times. */
long stm_start_transaction(stm_thread_local_t *tl);
void stm_start_inevitable_transaction(stm_thread_local_t *tl);
void stm_commit_transaction(void);

/* Abort the currently running transaction.  This function never
   returns: it jumps back to the stm_start_transaction(). */
void stm_abort_transaction(void) __attribute__((noreturn));

/* Turn the current transaction inevitable.
   The stm_become_inevitable() itself may still abort. */
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

/* Forces a safe-point if needed.  Normally not needed: this is
   automatic if you call stm_allocate(). */
static inline void stm_safe_point(void) {
    if (STM_SEGMENT->nursery_end <= _STM_NSE_SIGNAL_MAX)
        _stm_collectable_safe_point();
}

/* Forces a collection. */
void stm_collect(long level);

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
long stm_can_move(object_t *);

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
   commits. */
void stm_become_globally_unique_transaction(stm_thread_local_t *tl,
                                            const char *msg);


/* Temporary? */
void stm_flush_timing(stm_thread_local_t *tl, int verbose);


/* The markers pushed in the shadowstack are an odd number followed by a
   regular pointer.  When needed, this library invokes this callback to
   turn this pair into a human-readable explanation. */
extern void (*stmcb_expand_marker)(char *segment_base, uintptr_t odd_number,
                                   object_t *following_object,
                                   char *outputbuf, size_t outputbufsize);
extern void (*stmcb_debug_print)(const char *cause, double time,
                                 const char *marker);

/* Conventience macros to push the markers into the shadowstack */
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

char *_stm_expand_marker(void);


/* ==================== END ==================== */

#endif
