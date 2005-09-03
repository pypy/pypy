
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/


/* XXX hack to initialize the refcount of global structures: officially,
   we need a value equal to the number of references to this global from
   other globals, plus one.  This upper bound "approximation" will do... */
#define REFCOUNT_IMMORTAL  (INT_MAX/2)

#define OP_ZERO_MALLOC(size, r, err)  {                                 \
    r = (void*) PyObject_Malloc(size);                                  \
    if (r == NULL) FAIL_EXCEPTION(err, PyExc_MemoryError, "out of memory");\
    memset((void*) r, 0, size);                                         \
    COUNT_MALLOC;                                                       \
  }

#define OP_FREE(p)	{ PyObject_Free(p); COUNT_FREE; }

/* XXX uses officially bad fishing */
#define PUSH_ALIVE(obj) obj->refcount++

/*------------------------------------------------------------*/
#ifndef COUNT_OP_MALLOCS
/*------------------------------------------------------------*/

#define COUNT_MALLOC	/* nothing */
#define COUNT_FREE	/* nothing */

/*------------------------------------------------------------*/
#else /*COUNT_OP_MALLOCS*/
/*------------------------------------------------------------*/

static int count_mallocs=0, count_frees=0;

#define COUNT_MALLOC	count_mallocs++
#define COUNT_FREE	count_frees++

PyObject* malloc_counters(PyObject* self, PyObject* args)
{
  return Py_BuildValue("ii", count_mallocs, count_frees);
}

/*------------------------------------------------------------*/
#endif /*COUNT_OP_MALLOCS*/
/*------------------------------------------------------------*/

/* for Boehm GC */

#ifdef USING_BOEHM_GC

#define OP_BOEHM_ZERO_MALLOC(size, r, atomic, err)   {                         \
	r = (void*) GC_MALLOC##atomic(size);				       \
	if (r == NULL) FAIL_EXCEPTION(err, PyExc_MemoryError, "out of memory");	\
	memset((void*) r, 0, size);				       \
  }

#define OP_BOEHM_ZERO_MALLOC_FINALIZER(size, r, atomic, finalizer, err)   {    \
	r = (void*) GC_MALLOC##atomic(size);				       \
	if (r == NULL) FAIL_EXCEPTION(err, PyExc_MemoryError, "out of memory");	\
	GC_REGISTER_FINALIZER(r, finalizer, NULL, NULL, NULL);         \
	memset((void*) r, 0, size);				       \
  }

#undef PUSH_ALIVE
#define PUSH_ALIVE(obj)

#endif /* USING_BOEHM_GC */

/* for no GC */
#ifdef USING_NO_GC

#undef OP_ZERO_MALLOC

#define OP_ZERO_MALLOC(size, r, err)  {                                 \
    r = (void*) malloc(size);                                  \
    if (r == NULL) FAIL_EXCEPTION(err, PyExc_MemoryError, "out of memory");\
    memset((void*) r, 0, size);                                         \
    COUNT_MALLOC;                                                       \
  }

#undef PUSH_ALIVE
#define PUSH_ALIVE(obj)

#endif /* USING_NO_GC */
