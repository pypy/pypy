/* Imported by rpython/translator/stm/import_stmgc.py */
/*** Extendable Timestamps
 *
 * Documentation:
 * doc-*.txt
 *
 * This is very indirectly based on rstm_r5/stm/et.hpp.
 * See http://www.cs.rochester.edu/research/synchronization/rstm/api.shtml
 */

#ifndef _SRCSTM_ET_H
#define _SRCSTM_ET_H


#define MAX_THREADS         1024
#define LOCKED              (INTPTR_MAX - 2*(MAX_THREADS-1))

/* Description of the flags
 * ------------------------
 *
 * Objects are either "young" or "old" depending on the generational garbage
 * collection: "young" objects are the ones in the nursery (plus a few big
 * ones outside) and will be collected by the following minor collection.
 *
 * Additionally, objects are either "public", "protected" or "private".
 *
 * GCFLAG_OLD is set on old objects.
 *
 * GCFLAG_VISITED and GCFLAG_MARKED are used temporarily during major
 * collections.  The objects are MARKED|VISITED as soon as they have been
 * added to 'objects_to_trace', and so will be or have been traced.  The
 * objects are only MARKED if their memory must be kept alive, but (so far)
 * we found that tracing them is not useful.
 *
 * GCFLAG_PUBLIC is set on public objects.
 *
 * GCFLAG_BACKUP_COPY means the object is a (protected) backup copy.
 * For debugging.
 *
 * GCFLAG_PUBLIC_TO_PRIVATE is added to a *public* object that has got a
 * *private* copy.  It is sticky, reset only at the next major collection.
 *
 * GCFLAG_PREBUILT_ORIGINAL is only set on the original version of
 * prebuilt objects.
 *
 * GCFLAG_WRITE_BARRIER is set on *old* objects to track old-to-young
 * pointers.  It is only useful on private objects, and on protected
 * objects (which may be turned private again).  It may be left set on
 * public objects but is ignored there, because such objects are read-only.
 * The flag is removed once a write occurs and the object is recorded in
 * the list 'old_objects_to_trace'; it is set again at the next minor
 * collection.
 *
 * GCFLAG_MOVED is used temporarily during minor/major collections.
 *
 * GCFLAG_STUB is set for debugging on stub objects made by stealing or
 * by major collections.  'p_stub->h_revision' might be a value
 * that is == 2 (mod 4): in this case they point to a protected/private
 * object that belongs to the thread 'STUB_THREAD(p_stub)'.
 *
 * GCFLAG_PRIVATE_FROM_PROTECTED is set on objects that are private
 * but converted from a protected.  These are precisely the objects
 * that have a backup copy (in h_revision), which gives a copy of the
 * original protected object.
 * 
 * GCFLAG_HAS_ID is set on young objects that have an old reserved
 * memory to be copied to in minor collections (obj->h_original)
 * 
 * GCFLAG_WEAKREF is set on weakrefs. Only needed so that we can trace
 * the weakptr when stealing a weakref. Maybe a better solution is to
 * check the typeid?
 */
static const revision_t GCFLAG_OLD                    = STM_FIRST_GCFLAG << 0;
static const revision_t GCFLAG_VISITED                = STM_FIRST_GCFLAG << 1;
static const revision_t GCFLAG_PUBLIC                 = STM_FIRST_GCFLAG << 2;
static const revision_t GCFLAG_PREBUILT_ORIGINAL      = STM_FIRST_GCFLAG << 3;
// in stmgc.h:          GCFLAG_PUBLIC_TO_PRIVATE      = STM_FIRST_GCFLAG << 4;
// in stmgc.h:          GCFLAG_WRITE_BARRIER          = STM_FIRST_GCFLAG << 5;
// in stmgc.h:          GCFLAG_MOVED                  = STM_FIRST_GCFLAG << 6;
static const revision_t GCFLAG_BACKUP_COPY  /*debug*/ = STM_FIRST_GCFLAG << 7;
// in stmgc.h:          GCFLAG_STUB                   = STM_FIRST_GCFLAG << 8;
static const revision_t GCFLAG_PRIVATE_FROM_PROTECTED = STM_FIRST_GCFLAG << 9;
static const revision_t GCFLAG_HAS_ID                 = STM_FIRST_GCFLAG << 10;
static const revision_t GCFLAG_IMMUTABLE              = STM_FIRST_GCFLAG << 11;
static const revision_t GCFLAG_SMALLSTUB    /*debug*/ = STM_FIRST_GCFLAG << 12;
static const revision_t GCFLAG_MARKED                 = STM_FIRST_GCFLAG << 13;
static const revision_t GCFLAG_WEAKREF                = STM_FIRST_GCFLAG << 14;
/* warning, the last flag available is "<< 15" on 32-bit */


/* this value must be reflected in PREBUILT_FLAGS in stmgc.h */
#define GCFLAG_PREBUILT  (GCFLAG_VISITED           | \
                          GCFLAG_MARKED            | \
                          GCFLAG_PREBUILT_ORIGINAL | \
                          GCFLAG_OLD               | \
                          GCFLAG_PUBLIC)

#define GC_FLAG_NAMES  { "OLD",               \
                         "VISITED",           \
                         "PUBLIC",            \
                         "PREBUILT_ORIGINAL", \
                         "PUBLIC_TO_PRIVATE", \
                         "WRITE_BARRIER",     \
                         "MOVED",             \
                         "BACKUP_COPY",       \
                         "STUB",              \
                         "PRIVATE_FROM_PROTECTED", \
                         "HAS_ID",            \
                         "IMMUTABLE",         \
                         "SMALLSTUB",         \
                         "MARKED",            \
                         "WEAKREF",           \
                         NULL }

#define IS_POINTER(v)    (!((v) & 1))   /* even-valued number */

/************************************************************/

#define ABRT_MANUAL               0
#define ABRT_COMMIT               1
#define ABRT_STOLEN_MODIFIED      2
#define ABRT_VALIDATE_INFLIGHT    3
#define ABRT_VALIDATE_COMMIT      4
#define ABRT_VALIDATE_INEV        5
#define ABRT_COLLECT_MINOR        6
#define ABRT_COLLECT_MAJOR        7
#define ABORT_REASONS         8
#define ABORT_NAMES      { "MANUAL",            \
                           "COMMIT",            \
                           "STOLEN_MODIFIED",   \
                           "VALIDATE_INFLIGHT", \
                           "VALIDATE_COMMIT",   \
                           "VALIDATE_INEV",     \
                           "COLLECT_MINOR",     \
                           "COLLECT_MAJOR",     \
                         }

#define SPLP_ABORT                0
#define SPLP_LOCKED_INFLIGHT      1
#define SPLP_LOCKED_VALIDATE      2
#define SPLP_LOCKED_COMMIT        3
#define SPINLOOP_REASONS      4

/* this struct contains thread-local data that may be occasionally
 * accessed by a foreign thread and that must stay around after the
 * thread shuts down.  It is reused the next time a thread starts. */
struct tx_public_descriptor {
  revision_t collection_lock;
  struct stub_block_s *stub_blocks;
  gcptr stub_free_list;
  struct GcPtrList stolen_objects;
  struct GcPtrList stolen_young_stubs;
  revision_t free_list_next;

  GCPAGE_FIELDS_DECL
};

/* this struct contains all thread-local data that is never accessed
 * by a foreign thread */
struct tx_descriptor {
  struct tx_public_descriptor *public_descriptor;
  revision_t public_descriptor_index;
  jmp_buf *setjmp_buf;
  revision_t start_time;
  revision_t my_lock;
  gcptr *shadowstack;
  gcptr **shadowstack_end_ref;
  gcptr *thread_local_obj_ref;
  gcptr old_thread_local_obj;

  NURSERY_FIELDS_DECL

  long atomic;   /* 0 = not atomic, > 0 atomic */
  unsigned long count_reads;
  unsigned long reads_size_limit;        /* see should_break_tr. */
  unsigned long reads_size_limit_nonatomic;
  int active;    /* 0 = inactive, 1 = regular, 2 = inevitable,
                    negative = killed by collection */
  struct timespec start_real_time;
  int max_aborts;
  unsigned int num_commits;
  unsigned int num_aborts[ABORT_REASONS];
  unsigned int num_spinloops[SPINLOOP_REASONS];
  struct GcPtrList list_of_read_objects;
  struct GcPtrList private_from_protected;
  struct G2L public_to_private;
  struct GcPtrList abortinfo;
  char *longest_abort_info;
  long long longest_abort_info_time;
  revision_t *private_revision_ref;
  struct FXCache recent_reads_cache;
  char **read_barrier_cache_ref;
  struct tx_descriptor *tx_prev, *tx_next;
  int tcolor;
  pthread_t pthreadid;
  void *mem_clear_on_abort;
  size_t mem_bytes_to_clear_on_abort;
  struct G2L callbacks_on_abort;
};

extern __thread struct tx_descriptor *thread_descriptor;
extern __thread revision_t stm_private_rev_num;
extern struct tx_public_descriptor *stm_descriptor_array[];
extern struct tx_descriptor *stm_tx_head;

/************************************************************/


void BeginTransaction(jmp_buf *);
void BeginInevitableTransaction(void);  /* must save roots around this call */
void CommitTransaction(void);           /* must save roots around this call */
void BecomeInevitable(const char *why); /* must save roots around this call */
void AbortTransaction(int);
void AbortTransactionAfterCollect(struct tx_descriptor *, int);
void AbortNowIfDelayed(void);
void SpinLoop(int);

gcptr stm_DirectReadBarrier(gcptr);
gcptr stm_WriteBarrier(gcptr);
gcptr stm_RepeatReadBarrier(gcptr);
gcptr stm_ImmutReadBarrier(gcptr);
gcptr stm_RepeatWriteBarrier(gcptr);
gcptr _stm_nonrecord_barrier(gcptr);  /* debugging: read barrier, but
                                         not recording anything */
int _stm_is_private(gcptr);  /* debugging */
gcptr stm_get_private_from_protected(long);  /* debugging */
gcptr stm_get_read_obj(long);  /* debugging */
void stm_clear_read_cache(void);  /* debugging */
void _stm_test_forget_previous_state(void);  /* debugging */
_Bool stm_has_got_any_lock(struct tx_descriptor *);

struct tx_public_descriptor *stm_get_free_public_descriptor(revision_t *);
void DescriptorInit(void);
void DescriptorDone(void);

#ifdef _GC_DEBUG
char* stm_dbg_get_hdr_str(gcptr obj);
#endif
#endif  /* _ET_H */
