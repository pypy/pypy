#include "common_header.h"
#include "src/support.h"
#include <stdlib.h>
#include <stdio.h>


#ifdef RPY_STM
# include "src/mem.h"
# ifdef RPY_ASSERT
RPY_EXTERN
int try_pypy_debug_alloc_stop(void *);
# else
#  define try_pypy_debug_alloc_stop(p)  /* nothing */
# endif
void _pypy_stm_cb_free(void *ptr)
{
    /* This is called by src_stm/et.c when the transaction is aborted
       and the 'ptr' was malloced but not freed.  We have first to
       unregister the object with a tentative pypy_debug_alloc_stop(),
       which ignores it if it was not actually registered.  Then we
       free the object in the normal way.  Finally we increment the
       free counter to keep it in sync. */
    try_pypy_debug_alloc_stop(ptr);
    free(ptr);
    COUNT_FREE;
}
void _pypy_stm_op_free(void *ptr)
{
    /* Called when RPython code contains OP_FREE or OP_RAW_FREE.
     */
    if (stm_call_on_abort(&stm_thread_local, ptr, NULL) == 0) {
        /* There is a running non-inevitable transaction, but the object
           was not registered during it, which means that it was created
           before.  In this case, we cannot immediately free it, but
           only when a commit follows. */
        stm_call_on_commit(&stm_thread_local, ptr, _pypy_stm_cb_free);
    }
    else {
        /* In all other cases, free the object immediately. */
        _pypy_stm_cb_free(ptr);
    }
}
#endif


#ifdef COUNT_OP_MALLOCS
int count_mallocs=0, count_frees=0;
#endif


/***  tracking raw mallocs and frees for debugging ***/

#ifdef RPY_ASSERT

struct pypy_debug_alloc_s {
  struct pypy_debug_alloc_s *next;
  void *addr;
  const char *funcname;
};

static struct pypy_debug_alloc_s *pypy_debug_alloc_list = NULL;

#ifdef RPY_STM
// spinlock_acquire/spinlock_release defined in ../../stm/src_stm/stmgcintf.h
static uint8_t pypy_debug_alloc_lock = 0;
#else
# define stm_spinlock_acquire(lock)               /* nothing */
# define stm_spinlock_release(lock)               /* nothing */
#endif

RPY_EXTERN
void pypy_debug_alloc_start(void *addr, const char *funcname)
{
  struct pypy_debug_alloc_s *p = malloc(sizeof(struct pypy_debug_alloc_s));
  RPyAssert(p, "out of memory");
  p->addr = addr;
  p->funcname = funcname;
  stm_spinlock_acquire(pypy_debug_alloc_lock);
  p->next = pypy_debug_alloc_list;
  pypy_debug_alloc_list = p;
  stm_spinlock_release(pypy_debug_alloc_lock);
}

RPY_EXTERN
int try_pypy_debug_alloc_stop(void *addr)
{
  struct pypy_debug_alloc_s **p;
  if (!addr)
	return 1;
  stm_spinlock_acquire(pypy_debug_alloc_lock);
  for (p = &pypy_debug_alloc_list; *p; p = &((*p)->next))
    if ((*p)->addr == addr)
      {
        struct pypy_debug_alloc_s *dying;
        dying = *p;
        *p = dying->next;
        stm_spinlock_release(pypy_debug_alloc_lock);
        free(dying);
        return 1;
      }
  stm_spinlock_release(pypy_debug_alloc_lock);
  return 0;
}

RPY_EXTERN
void pypy_debug_alloc_stop(void *addr)
{
  if (!try_pypy_debug_alloc_stop(addr))
    RPyAssert(0, "free() of a never-malloc()ed object");
}

RPY_EXTERN
void pypy_debug_alloc_results(void)
{
  long count = 0;
  struct pypy_debug_alloc_s *p;
  stm_spinlock_acquire(pypy_debug_alloc_lock);
  for (p = pypy_debug_alloc_list; p; p = p->next)
    count++;
  if (count > 0)
    {
      char *env = getenv("PYPY_ALLOC");
      fprintf(stderr, "mem.c: %ld mallocs left", count);
      if (env && *env)
        {
          fprintf(stderr, " (most recent first):\n");
          for (p = pypy_debug_alloc_list; p; p = p->next)
            fprintf(stderr, "    %p  %s\n", p->addr, p->funcname);
        }
      else
        fprintf(stderr, " (use PYPY_ALLOC=1 to see the list)\n");
    }
  stm_spinlock_release(pypy_debug_alloc_lock);
}

#endif /* RPY_ASSERT */


/* Boehm GC helper functions */

#ifdef PYPY_USING_BOEHM_GC

struct boehm_fq_s {
    void *obj;
    struct boehm_fq_s *next;
};
RPY_EXTERN void (*boehm_fq_trigger[])(void);

int boehm_gc_finalizer_lock = 0;
void boehm_gc_finalizer_notifier(void)
{
    int i;

    boehm_gc_finalizer_lock++;
    while (GC_should_invoke_finalizers()) {
        if (boehm_gc_finalizer_lock > 1) {
            /* GC_invoke_finalizers() will be done by the
               boehm_gc_finalizer_notifier() that is
               currently in the C stack, when we return there */
            break;
        }
        GC_invoke_finalizers();
    }

    i = 0;
    while (boehm_fq_trigger[i])
        boehm_fq_trigger[i++]();

    boehm_gc_finalizer_lock--;
}

static void mem_boehm_ignore(char *msg, GC_word arg)
{
}

void boehm_gc_startup_code(void)
{
    GC_init();
    GC_finalizer_notifier = &boehm_gc_finalizer_notifier;
    GC_finalize_on_demand = 1;
    GC_set_warn_proc(mem_boehm_ignore);
}

void boehm_fq_callback(void *obj, void *rawfqueue)
{
    struct boehm_fq_s **fqueue = rawfqueue;
    struct boehm_fq_s *node = GC_malloc(sizeof(void *) * 2);
    if (!node)
        return;   /* ouch, too bad */
    node->obj = obj;
    node->next = *fqueue;
    *fqueue = node;
}

void *boehm_fq_next_dead(struct boehm_fq_s **fqueue)
{
    struct boehm_fq_s *node = *fqueue;
    if (node != NULL) {
        *fqueue = node->next;
        return node->obj;
    }
    else
        return NULL;
}
#endif /* BOEHM GC */


#ifdef RPY_ASSERT
# ifdef PYPY_USE_ASMGCC
#  include "structdef.h"
#  include "forwarddecl.h"
# endif
void pypy_check_stack_count(void)
{
# ifdef PYPY_USE_ASMGCC
    void *anchor = (void*)&pypy_g_ASM_FRAMEDATA_HEAD;
    void *fd = ((void* *) (((char *)anchor) + sizeof(void*)))[0];
    long got = 0;
    long stacks_counter =
       pypy_g_rpython_rtyper_lltypesystem_rffi_StackCounter.sc_inst_stacks_counter;
    while (fd != anchor) {
        got += 1;
        fd = ((void* *) (((char *)fd) + sizeof(void*)))[0];
    }
    RPyAssert(rpy_fastgil == 1,
              "pypy_check_stack_count doesn't have the GIL");
    RPyAssert(got == stacks_counter - 1,
              "bad stacks_counter or non-closed stacks around");
# endif
}
#endif
