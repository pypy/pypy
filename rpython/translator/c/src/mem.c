#include "common_header.h"
#include "src/support.h"
#include <stdlib.h>
#include <stdio.h>


#ifdef RPY_STM
# include "src/mem.h"
# include "src/allocator.h"
# ifdef RPY_ASSERT
int try_pypy_debug_alloc_stop(void *);
# else
#  define try_pypy_debug_alloc_stop(p)  /* nothing */
# endif
void _pypy_stm_free(void *ptr)
{
    /* This is called by src_stm/et.c when the transaction is aborted
       and the 'ptr' was malloced but not freed.  We have first to
       unregister the object with a tentative pypy_debug_alloc_stop(),
       which ignores it if it was not actually registered.  Then we
       free the object in the normal way.  Finally we increment the
       free counter to keep it in sync. */
    try_pypy_debug_alloc_stop(ptr);
    PyObject_Free(ptr);
    COUNT_FREE;
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
static Signed pypy_debug_alloc_lock = 0;
#else
# define spinlock_acquire(lock, targetvalue)  /* nothing */
# define spinlock_release(lock)               /* nothing */
#endif

void pypy_debug_alloc_start(void *addr, const char *funcname)
{
  struct pypy_debug_alloc_s *p = malloc(sizeof(struct pypy_debug_alloc_s));
  RPyAssert(p, "out of memory");
  p->addr = addr;
  p->funcname = funcname;
  spinlock_acquire(pypy_debug_alloc_lock, '+');
  p->next = pypy_debug_alloc_list;
  pypy_debug_alloc_list = p;
  spinlock_release(pypy_debug_alloc_lock);
}

int try_pypy_debug_alloc_stop(void *addr)
{
  struct pypy_debug_alloc_s **p;
  spinlock_acquire(pypy_debug_alloc_lock, '-');
  for (p = &pypy_debug_alloc_list; *p; p = &((*p)->next))
    if ((*p)->addr == addr)
      {
        struct pypy_debug_alloc_s *dying;
        dying = *p;
        *p = dying->next;
        spinlock_release(pypy_debug_alloc_lock);
        free(dying);
        return 1;
      }
  spinlock_release(pypy_debug_alloc_lock);
  return 0;
}

void pypy_debug_alloc_stop(void *addr)
{
  if (!try_pypy_debug_alloc_stop(addr))
    RPyAssert(0, "free() of a never-malloc()ed object");
}

void pypy_debug_alloc_results(void)
{
  long count = 0;
  struct pypy_debug_alloc_s *p;
  spinlock_acquire(pypy_debug_alloc_lock, 'R');
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
  spinlock_release(pypy_debug_alloc_lock);
}

#endif /* RPY_ASSERT */


/* Boehm GC helper functions */

#ifdef PYPY_USING_BOEHM_GC

int boehm_gc_finalizer_lock = 0;
void boehm_gc_finalizer_notifier(void)
{
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
    RPyAssert(got == stacks_counter - 1,
              "bad stacks_counter or non-closed stacks around");
# endif
}
#endif
