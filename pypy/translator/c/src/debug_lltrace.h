
void _RPyTraceSet(void *addr, long newvalue, long mark);


#ifndef RPY_LL_TRACE /****************************************/


#  define RPY_IS_TRACING           0
#  define RPyTraceSet(ptr, mark)   /* nothing */
#  ifndef PYPY_NOT_MAIN_FILE
void _RPyTraceSet(void *addr, long newvalue, long mark) { }
#  endif


#else /*******************************************************/


#  define RPY_IS_TRACING           1
#  define RPyTraceSet(ptr, mark)   _RPyTraceSet(&(ptr), (long)(ptr), mark)

#  ifndef PYPY_NOT_MAIN_FILE

struct _RPyTrace_s {
  long mark;
  void *addr;
  long newvalue;
};

static struct _RPyTrace_s *_RPyTrace_start   = NULL;
static struct _RPyTrace_s *_RPyTrace_stop    = NULL;
static struct _RPyTrace_s *_RPyTrace_current = NULL;
static const long _RPyTrace_default_size = 134217728;

void _RPyTrace_WrapAround(void)
{
  if (_RPyTrace_start == NULL)
    {
      char *csize = getenv("PYPYTRACEBUF");
      long size = csize ? atol(csize) : 0;
      if (size <= 1)
        size = _RPyTrace_default_size;
      _RPyTrace_start = malloc(size * sizeof(struct _RPyTrace_s));
      RPyAssert(_RPyTrace_start, "not enough memory to allocate the trace");
      _RPyTrace_stop = _RPyTrace_start + size;
    }
  _RPyTrace_current = _RPyTrace_start;
  fprintf(stderr, "lltrace: buffer from %p to %p, size %ld entries\n",
          _RPyTrace_start, _RPyTrace_stop,
          (long)(_RPyTrace_stop - _RPyTrace_start));
}

void _RPyTraceSet(void *addr, long newvalue, long mark)
{
  if (_RPyTrace_current == _RPyTrace_stop)
    _RPyTrace_WrapAround();
  _RPyTrace_current->mark = mark;
  _RPyTrace_current->addr = addr;
  _RPyTrace_current->newvalue = newvalue;
  ++_RPyTrace_current;
}

#  endif


#endif /******************************************************/
