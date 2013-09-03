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

void pypy_debug_alloc_start(void *addr, const char *funcname)
{
  struct pypy_debug_alloc_s *p = malloc(sizeof(struct pypy_debug_alloc_s));
  RPyAssert(p, "out of memory");
  p->next = pypy_debug_alloc_list;
  p->addr = addr;
  p->funcname = funcname;
  pypy_debug_alloc_list = p;
}

void pypy_debug_alloc_stop(void *addr)
{
  struct pypy_debug_alloc_s **p;
  for (p = &pypy_debug_alloc_list; *p; p = &((*p)->next))
    if ((*p)->addr == addr)
      {
        struct pypy_debug_alloc_s *dying;
        dying = *p;
        *p = dying->next;
        free(dying);
        return;
      }
  RPyAssert(0, "free() of a never-malloc()ed object");
}

void pypy_debug_alloc_results(void)
{
  long count = 0;
  struct pypy_debug_alloc_s *p;
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
