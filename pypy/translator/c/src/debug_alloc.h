/**************************************************************/
 /***  tracking raw mallocs and frees for debugging          ***/

#ifndef RPY_ASSERT

#  define OP_TRACK_ALLOC_START(addr, r)   /* nothing */
#  define OP_TRACK_ALLOC_STOP(addr, r)    /* nothing */

#else   /* ifdef RPY_ASSERT */

#  define OP_TRACK_ALLOC_START(addr, r)  pypy_debug_alloc_start(addr, \
                                                                __FUNCTION__)
#  define OP_TRACK_ALLOC_STOP(addr, r)   pypy_debug_alloc_stop(addr)

void pypy_debug_alloc_start(void*, const char*);
void pypy_debug_alloc_stop(void*);
void pypy_debug_alloc_results(void);

/************************************************************/


#ifndef PYPY_NOT_MAIN_FILE

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

#endif


#endif  /* RPY_ASSERT */
