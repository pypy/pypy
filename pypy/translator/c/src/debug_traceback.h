/**************************************************************/
 /***  C header subsection: RPython tracebacks for debugging ***/


/* We store a list of (location, exctype) in a circular buffer that
   we hope is large enough.  Example of how to interpret the content
   of the buffer:

       location   exctype      meaning

       NULL       &KeyError    a KeyError was raised
       h:5        NULL         it was raised at h:5
       g:12       NULL         which itself was called from g:12
       f:17       &KeyError    called from f:17, where a finally block starts
       ...                     ...more exceptions can occur...
       RERAISE    &KeyError    eventually the KeyError is re-raised by f
       entry:25   NULL         which itself was called from entry:25

   Note that decoding the buffer assumes that when exctype matches, it was
   really the same exception, for the purpose of going back from the RERAISE
   line to the f:17/KeyError line.
*/

#ifdef RPY_LL_ASSERT
#  define PYPY_DEBUG_TRACEBACK_DEPTH        8192    /* a power of two */
#else
#  define PYPY_DEBUG_TRACEBACK_DEPTH        128     /* a power of two */
#endif

#define PYPYDTPOS_RERAISE                 ((struct pypydtpos_s *) -1)
#define PYPYDTSTORE(loc, etype)                         \
  pypy_debug_tracebacks[pypydtcount].location = loc;    \
  pypy_debug_tracebacks[pypydtcount].exctype = etype;   \
  pypydtcount = (pypydtcount + 1) & (PYPY_DEBUG_TRACEBACK_DEPTH-1)

#define OP_DEBUG_START_TRACEBACK(etype, _)  PYPYDTSTORE(NULL, etype)
#define OP_DEBUG_RERAISE_TRACEBACK(etp, _)  PYPYDTSTORE(PYPYDTPOS_RERAISE, etp)
#define OP_DEBUG_PRINT_TRACEBACK()          pypy_debug_traceback_print()

#define PYPY_DEBUG_RECORD_TRACEBACK(funcname)   {       \
    static struct pypydtpos_s loc = {                   \
      PYPY_FILE_NAME, funcname, __LINE__ };             \
    PYPYDTSTORE(&loc, NULL);                            \
  }
#define PYPY_DEBUG_CATCH_EXCEPTION(funcname, etype, is_fatal)   {       \
    static struct pypydtpos_s loc = {                                   \
      PYPY_FILE_NAME, funcname, __LINE__ };                             \
    PYPYDTSTORE(&loc, etype);                                           \
    if (is_fatal) pypy_debug_catch_fatal_exception();                   \
  }

struct pypydtpos_s {
  const char *filename;
  const char *funcname;
  int lineno;
};

struct pypydtentry_s {
  struct pypydtpos_s *location;
  void *exctype;
};

extern int pypydtcount;
extern struct pypydtentry_s pypy_debug_tracebacks[PYPY_DEBUG_TRACEBACK_DEPTH];

void pypy_debug_traceback_print(void);
void pypy_debug_catch_fatal_exception(void);


/************************************************************/


#ifndef PYPY_NOT_MAIN_FILE

int pypydtcount = 0;
struct pypydtentry_s pypy_debug_tracebacks[PYPY_DEBUG_TRACEBACK_DEPTH];

void pypy_debug_traceback_print(void)
{
  int i;
  int skipping;
  void *my_etype = RPyFetchExceptionType();
  struct pypydtpos_s *location;
  void *etype;
  int has_loc;

  /* This code parses the pypy_debug_tracebacks array.  See example
     at the start of the file. */
  fprintf(stderr, "RPython traceback:\n");
  skipping = 0;
  i = pypydtcount;
  while (1)
    {
      i = (i - 1) & (PYPY_DEBUG_TRACEBACK_DEPTH-1);
      if (i == pypydtcount)
        {
          fprintf(stderr, "  ...\n");
          break;
        }

      location = pypy_debug_tracebacks[i].location;
      etype    = pypy_debug_tracebacks[i].exctype;
      has_loc  = location != NULL && location != PYPYDTPOS_RERAISE;

      if (skipping && has_loc && etype == my_etype)
        skipping = 0;     /* found the matching "f:17, &KeyError */

      if (!skipping)
        {
          if (has_loc)
            fprintf(stderr, "  File \"%s\", line %d, in %s\n",
                    location->filename, location->lineno, location->funcname);
          else
            {
              /* line "NULL, &KeyError" or "RERAISE, &KeyError" */
              if (!my_etype)
                my_etype = etype;
              if (etype != my_etype)
                {
                  fprintf(stderr, "  Note: this traceback is "
                                  "incomplete or corrupted!\n");
                  break;
                }
              if (location == NULL)  /* found the place that raised the exc */
                break;
              skipping = 1;     /* RERAISE: skip until "f:17, &KeyError" */
            }
        }
    }
}

void pypy_debug_catch_fatal_exception(void)
{
  pypy_debug_traceback_print();
  fprintf(stderr, "Fatal RPython error: %s\n",
          RPyFetchExceptionType()->ov_name->items);
  abort();
}

#endif /* PYPY_NOT_MAIN_FILE */
