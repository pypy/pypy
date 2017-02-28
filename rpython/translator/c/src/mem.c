#include "common_header.h"
#include "src/support.h"
#include <stdlib.h>
#include <stdio.h>

/***  tracking raw mallocs and frees for debugging ***/

#ifdef RPY_ASSERT

struct pypy_debug_alloc_s {
  struct pypy_debug_alloc_s *next;
  void *addr;
  const char *funcname;
};

static struct pypy_debug_alloc_s *pypy_debug_alloc_list = NULL;

static rpy_spinlock_t pypy_debug_alloc_lock = 0;

RPY_EXTERN
void pypy_debug_alloc_start(void *addr, const char *funcname)
{
  struct pypy_debug_alloc_s *p = malloc(sizeof(struct pypy_debug_alloc_s));
  RPyAssert(p, "out of memory");
  p->addr = addr;
  p->funcname = funcname;
  rpy_spinlock_acquire(&pypy_debug_alloc_lock);
  p->next = pypy_debug_alloc_list;
  pypy_debug_alloc_list = p;
  rpy_spinlock_release(&pypy_debug_alloc_lock);
}

RPY_EXTERN
void pypy_debug_alloc_stop(void *addr)
{
  struct pypy_debug_alloc_s **p;
  if (!addr)
	return;
  rpy_spinlock_acquire(&pypy_debug_alloc_lock);
  for (p = &pypy_debug_alloc_list; *p; p = &((*p)->next))
    if ((*p)->addr == addr)
      {
        struct pypy_debug_alloc_s *dying;
        dying = *p;
        *p = dying->next;
        rpy_spinlock_release(&pypy_debug_alloc_lock);
        free(dying);
        return;
      }
  RPyAssert(0, "free() of a never-malloc()ed object");
}

RPY_EXTERN
void pypy_debug_alloc_results(void)
{
  long count = 0;
  struct pypy_debug_alloc_s *p;
  rpy_spinlock_acquire(&pypy_debug_alloc_lock);
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
  rpy_spinlock_release(&pypy_debug_alloc_lock);
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
