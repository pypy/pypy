/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STMGC_H
#define _STMGC_H

#include <stdlib.h>
#include <stdint.h>


typedef intptr_t revision_t;
typedef uintptr_t urevision_t;

typedef struct stm_object_s {
    revision_t h_tid;
    revision_t h_revision;
    revision_t h_original;
} *gcptr;


/* by convention the lower half of _tid is used to store the object type */
#define stm_get_tid(o)       ((o)->h_tid & STM_USER_TID_MASK)
#define stm_set_tid(o, tid)  ((o)->h_tid = ((o)->h_tid & ~STM_USER_TID_MASK) \
                                           | (tid))

#define STM_SIZE_OF_USER_TID       (sizeof(revision_t) / 2)    /* in bytes */
#define STM_FIRST_GCFLAG           (1L << (8 * STM_SIZE_OF_USER_TID))
#define STM_USER_TID_MASK          (STM_FIRST_GCFLAG - 1)
#define PREBUILT_FLAGS             (STM_FIRST_GCFLAG * ((1<<0) | (1<<1) |    \
                                               (1<<2) | (1<<3) | (1<<13)))
#define PREBUILT_REVISION          1


/* push roots around allocating functions! */

/* allocate an object out of the local nursery */
gcptr stm_allocate(size_t size, unsigned long tid);
/* allocate an object that is be immutable. it cannot be changed with
   a stm_write_barrier() or after the next commit */
gcptr stm_allocate_immutable(size_t size, unsigned long tid);

/* allocates a public reference to the object that will 
   not be freed until stm_unregister_integer_address is 
   called on the result */
intptr_t stm_allocate_public_integer_address(gcptr);
void stm_unregister_integer_address(intptr_t);


/* returns a never changing hash for the object */
revision_t stm_hash(gcptr);
/* returns a number for the object which is unique during its lifetime */
revision_t stm_id(gcptr);
/* returns nonzero if the two object-copy pointers belong to the
same original object */
_Bool stm_pointer_equal(gcptr, gcptr);
_Bool stm_pointer_equal_prebuilt(gcptr, gcptr); /* 2nd arg is known prebuilt */

/* to push/pop objects into the local shadowstack */
#if 0     // (optimized version below)
void stm_push_root(gcptr);
gcptr stm_pop_root(void);
#endif

/* initialize/deinitialize the stm framework in the current thread */
void stm_initialize(void);
void stm_finalize(void);

/* alternate initializers/deinitializers, to use for places that may or
   may not be recursive, like callbacks from C code.  The return value
   of the first one must be passed as argument to the second. */
int stm_enter_callback_call(void);
void stm_leave_callback_call(int);

/* read/write barriers.

   - the read barrier must be applied before reading from an object.
     the result is valid as long as we're in the same transaction,
     and stm_write_barrier() is not called on the same object.

   - the write barrier must be applied before writing to an object.
     the result is valid for a shorter period of time: we have to
     do stm_write_barrier() again if we ended the transaction, or
     if we did a potential collection (e.g. stm_allocate()).

   - as an optimization, stm_repeat_read_barrier() can be used
     instead of stm_read_barrier() if the object was already
     obtained by a stm_read_barrier() in the same transaction.
     The only thing that may have occurred is that a
     stm_write_barrier() on the same object could have made it
     invalid.

   - a different optimization is to read immutable fields: in order
     to do that, use stm_immut_read_barrier(), which only activates
     on stubs.

   - stm_repeat_write_barrier() can be used on an object on which
     we already did stm_write_barrier(), but a potential collection
     can have occurred.

   - stm_write_barrier_noptr() is a slightly cheaper version of
     stm_write_barrier(), for when we are going to write
     non-gc-pointers into the object.
*/
#if 0     // (optimized version below)
gcptr stm_read_barrier(gcptr);
gcptr stm_write_barrier(gcptr);
gcptr stm_repeat_read_barrier(gcptr);
gcptr stm_immut_read_barrier(gcptr);
gcptr stm_repeat_write_barrier(gcptr);   /* <= always returns its argument */
gcptr stm_write_barrier_noptr(gcptr);
#endif

/* start a new transaction, calls callback(), and when it returns
   finish that transaction.  callback() is called with the 'arg'
   provided, and with a retry_counter number.  Must save roots around
   this call.  The callback() is called repeatedly as long as it
   returns a value > 0. */
void stm_perform_transaction(gcptr arg, int (*callback)(gcptr, int));

/* finish the current transaction, start a new one, or turn the current
   transaction inevitable.  Must save roots around calls to these three
   functions. */
void stm_commit_transaction(void);
void stm_begin_inevitable_transaction(void);
void stm_become_inevitable(const char *reason);

/* debugging: check if we're currently running a transaction or not. */
int stm_in_transaction(void);

/* change the default transaction length, and ask if now would be a good
   time to break the transaction (by returning from the 'callback' above
   with a positive value). */
void stm_set_transaction_length(long length_max);
_Bool stm_should_break_transaction(void);

/* change the atomic counter by 'delta' and return the new value.  Used
   with +1 to enter or with -1 to leave atomic mode, or with 0 to just
   know the current value of the counter.  The current transaction is
   *never* interrupted as long as this counter is positive. */
long stm_atomic(long delta);


/* callback: get the size of an object */
extern size_t stmcb_size(gcptr);

/* callback: trace the content of an object */
extern void stmcb_trace(gcptr, void visit(gcptr *));

/* You can put one GC-tracked thread-local object here.
   (Obviously it can be a container type containing more GC objects.)
   It is set to NULL by stm_initialize(). */
extern __thread gcptr stm_thread_local_obj;

/* For tracking where aborts occurs, you can push/pop information
   into this stack.  When an abort occurs this information is encoded
   and flattened into a buffer which can later be retrieved with
   stm_inspect_abort_info().  (XXX details not documented yet) */
void stm_abort_info_push(gcptr obj, long fieldoffsets[]);
void stm_abort_info_pop(long count);
char *stm_inspect_abort_info(void);    /* turns inevitable */

/* mostly for debugging support */
void stm_abort_and_retry(void);
void stm_minor_collect(void);
void stm_major_collect(void);

/* weakref support: allocate a weakref object, and set it to point
   weakly to 'obj'.  The weak pointer offset is hard-coded to be at
   'size - WORD'.  Important: stmcb_trace() must NOT trace it.
   Weakrefs are *immutable*!  Don't attempt to use stm_write_barrier()
   on them. */
gcptr stm_weakref_allocate(size_t size, unsigned long tid, gcptr obj);



/****************  END OF PUBLIC INTERFACE  *****************/
/************************************************************/

/* Clear some memory when aborting a transaction in the current
   thread. This is a provisional API. The information is stored
   in the current tx_descriptor. */
void stm_clear_on_abort(void *start, size_t bytes);

/* If the current transaction aborts later, invoke 'callback(key)'.
   If the current transaction commits, then the callback is forgotten.
   You can only register one callback per key.  You can call
   'stm_call_on_abort(key, NULL)' to cancel an existing callback. */
void stm_call_on_abort(void *key, void callback(void *));

/* only user currently is stm_allocate_public_integer_address() */
void stm_register_integer_address(intptr_t);

/* macro functionality */

extern __thread gcptr *stm_shadowstack;

#define stm_push_root(obj)  (*stm_shadowstack++ = (obj))
#define stm_pop_root()      (*--stm_shadowstack)

extern __thread revision_t stm_private_rev_num;
gcptr stm_DirectReadBarrier(gcptr);
gcptr stm_WriteBarrier(gcptr);
gcptr stm_RepeatReadBarrier(gcptr);
gcptr stm_ImmutReadBarrier(gcptr);
gcptr stm_RepeatWriteBarrier(gcptr);
static const revision_t GCFLAG_PUBLIC_TO_PRIVATE = STM_FIRST_GCFLAG << 4;
static const revision_t GCFLAG_WRITE_BARRIER = STM_FIRST_GCFLAG << 5;
static const revision_t GCFLAG_MOVED = STM_FIRST_GCFLAG << 6;
static const revision_t GCFLAG_STUB = STM_FIRST_GCFLAG << 8;
extern __thread char *stm_read_barrier_cache;
#define FX_MASK 65535
#define FXCACHE_AT(obj)  \
    (*(gcptr *)(stm_read_barrier_cache + ((revision_t)(obj) & FX_MASK)))

#define UNLIKELY(test)  __builtin_expect(test, 0)

#ifdef STM_BARRIER_COUNT
# define STM_BARRIER_NUMBERS  12
# define STM_BARRIER_NAMES "stm_read_barrier\n"         \
                           "stm_write_barrier\n"        \
                           "stm_repeat_read_barrier\n"  \
                           "stm_immut_read_barrier\n"   \
                           "stm_repeat_write_barrier\n" \
                           "stm_write_barrier_noptr\n"
# define STM_COUNT(id, x)  (stm_barriercount[id]++, x)
extern long stm_barriercount[STM_BARRIER_NUMBERS];
#else
# define STM_COUNT(id, x)  (x)
#endif

#define stm_read_barrier(obj)                                   \
    (UNLIKELY(((obj)->h_revision != stm_private_rev_num) &&     \
              (FXCACHE_AT(obj) != (obj))) ?                     \
        STM_COUNT(0, stm_DirectReadBarrier(obj))                \
     :  STM_COUNT(1, obj))

#define stm_write_barrier(obj)                                  \
    (UNLIKELY(((obj)->h_revision != stm_private_rev_num) ||     \
              (((obj)->h_tid & GCFLAG_WRITE_BARRIER) != 0)) ?   \
        STM_COUNT(2, stm_WriteBarrier(obj))                     \
     :  STM_COUNT(3, obj))

#define stm_repeat_read_barrier(obj)                            \
    (UNLIKELY(((obj)->h_tid & (GCFLAG_PUBLIC_TO_PRIVATE |       \
                               GCFLAG_MOVED)) != 0) ?           \
        STM_COUNT(4, stm_RepeatReadBarrier(obj))                \
     :  STM_COUNT(5, obj))

#define stm_immut_read_barrier(obj)                             \
    (UNLIKELY(((obj)->h_tid & GCFLAG_STUB) != 0) ?              \
        STM_COUNT(6, stm_ImmutReadBarrier(obj))                 \
     :  STM_COUNT(7, obj))

#define stm_repeat_write_barrier(obj)                           \
    (UNLIKELY(((obj)->h_tid & GCFLAG_WRITE_BARRIER) != 0) ?     \
        STM_COUNT(8, stm_RepeatWriteBarrier(obj))               \
     :  STM_COUNT(9, obj))

#define stm_write_barrier_noptr(obj)                            \
    (UNLIKELY((obj)->h_revision != stm_private_rev_num) ?       \
        STM_COUNT(10, stm_WriteBarrier(obj))                    \
     :  STM_COUNT(11, obj))


#endif
