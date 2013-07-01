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
#define PREBUILT_FLAGS             (STM_FIRST_GCFLAG * (1 + 2 + 4 + 8))
#define PREBUILT_REVISION          1


/* allocate an object out of the local nursery */
gcptr stm_allocate(size_t size, unsigned long tid);

/* returns a never changing hash for the object */
revision_t stm_hash(gcptr);
/* returns a number for the object which is unique during its lifetime */
revision_t stm_id(gcptr);
/* returns nonzero if the two object-copy pointers belong to the
same original object */
_Bool stm_pointer_equal(gcptr, gcptr);

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

/* read/write barriers (the most general versions only for now) */
#if 0     // (optimized version below)
gcptr stm_read_barrier(gcptr);
gcptr stm_write_barrier(gcptr);
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



/* macro-like functionality */

extern __thread gcptr *stm_shadowstack;

static inline void stm_push_root(gcptr obj) {
    *stm_shadowstack++ = obj;
}
static inline gcptr stm_pop_root(void) {
    return *--stm_shadowstack;
}

extern __thread revision_t stm_private_rev_num;
gcptr stm_DirectReadBarrier(gcptr);
gcptr stm_WriteBarrier(gcptr);
static const revision_t GCFLAG_WRITE_BARRIER = STM_FIRST_GCFLAG << 5;
extern __thread char *stm_read_barrier_cache;
#define FX_MASK 65535
#define FXCACHE_AT(obj)  \
    (*(gcptr *)(stm_read_barrier_cache + ((revision_t)(obj) & FX_MASK)))

#define UNLIKELY(test)  __builtin_expect(test, 0)
static inline gcptr stm_read_barrier(gcptr obj) {
    /* XXX optimize to get the smallest code */
    if (UNLIKELY((obj->h_revision != stm_private_rev_num) &&
                 (FXCACHE_AT(obj) != obj)))
        obj = stm_DirectReadBarrier(obj);
    return obj;
}

static inline gcptr stm_write_barrier(gcptr obj) {
    if (UNLIKELY((obj->h_revision != stm_private_rev_num) |
                 ((obj->h_tid & GCFLAG_WRITE_BARRIER) != 0)))
        obj = stm_WriteBarrier(obj);
    return obj;
}
#undef UNLIKELY


#endif
