/* allocation functions */
#include "common_header.h"
#include "src/support.h"
#include <malloc.h>
#include <stdlib.h>

#if defined(PYPY_USE_TRIVIAL_MALLOC)
  void *PyObject_Malloc(size_t n) { return malloc(n); }
  void *PyObject_Realloc(void *p, size_t n) { return realloc(p, n); }
  void PyObject_Free(void *p) { if (p) { *((int*)p) = 0xDDDDDDDD; } free(p); }

#elif defined(PYPY_USE_LINUXMEMCHK)
#  include "linuxmemchk.c"

#elif defined(PYPY_NO_OBMALLOC)
  void *PyObject_Malloc(size_t n) { return malloc(n); }
  void *PyObject_Realloc(void *p, size_t n) { return realloc(p, n); }
  void PyObject_Free(void *p) { free(p); }

#else
#  ifndef WITH_PYMALLOC
#    define WITH_PYMALLOC
#  endif
/* The same obmalloc as CPython */
#  include "src/obmalloc.c"

#endif


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
      fprintf(stderr, "debug_alloc.h: %ld mallocs left", count);
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
