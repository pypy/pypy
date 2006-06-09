
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/

#define OP_RAW_MALLOC(size,r) OP_ZERO_MALLOC(size, r)

#define OP_RAW_MALLOC_USAGE(size, r) r = size

#ifdef MS_WINDOWS
#define alloca  _alloca
#endif

#define OP_STACK_MALLOC(size,r)                                            \
    r = (void*) alloca(size);                                              \
    if (r == NULL) FAIL_EXCEPTION(PyExc_MemoryError, "out of memory");\
 
#define OP_RAW_FREE(x)             OP_FREE(x)
#define OP_RAW_MEMCOPY(x,y,size,r) memcpy(y,x,size);

/************************************************************/

/* a reasonably safe bound on the largest allowed argument value
   that we can pass to malloc.  This is used for var-sized mallocs
   to compute the largest allowed number of items in the array. */
#define MAXIMUM_MALLOCABLE_SIZE   (LONG_MAX-4096)

#define OP_MAX_VARSIZE(numitems, itemtype)  {			\
    if (((unsigned long)(numitems)) >					\
		(MAXIMUM_MALLOCABLE_SIZE / sizeof(itemtype)))		\
        FAIL_EXCEPTION(PyExc_MemoryError, "addr space overflow");	\
  } 


/* XXX hack to initialize the refcount of global structures: officially,
   we need a value equal to the number of references to this global from
   other globals, plus one.  This upper bound "approximation" will do... */
#define REFCOUNT_IMMORTAL  (INT_MAX/2)

#define OP_ZERO_MALLOC(size, r)  {                                      \
    r = (void*) PyObject_Malloc(size);                                  \
    if (r == NULL) {FAIL_EXCEPTION(PyExc_MemoryError, "out of memory"); } \
    else {                                                              \
        memset((void*) r, 0, size);                                     \
        COUNT_MALLOC;                                                   \
    }                                                                   \
  }

#define OP_FREE(p)	{ PyObject_Free(p); COUNT_FREE; }

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

#define BOEHM_MALLOC_0_0   GC_MALLOC
#define BOEHM_MALLOC_1_0   GC_MALLOC_ATOMIC
#define BOEHM_MALLOC_0_1   GC_MALLOC
#define BOEHM_MALLOC_1_1   GC_MALLOC_ATOMIC
/* #define BOEHM_MALLOC_0_1   GC_MALLOC_IGNORE_OFF_PAGE */
/* #define BOEHM_MALLOC_1_1   GC_MALLOC_ATOMIC_IGNORE_OFF_PAGE */

#define OP_BOEHM_ZERO_MALLOC(size, r, is_atomic, is_varsize)   {             \
	r = (void*) BOEHM_MALLOC_ ## is_atomic ## _ ## is_varsize (size);    \
	if (r == NULL) {FAIL_EXCEPTION(PyExc_MemoryError, "out of memoy");}  \
        else {                                                               \
            if (is_atomic)  /* the non-atomic versions return cleared memory */  \
                memset((void*) r, 0, size);                                   \
        }                                                                     \
  }

/* as we said in rbuiltin.py: 
# XXX this next little bit is a monstrous hack.  the Real Thing awaits
# some kind of proper GC integration
if GC integration has happened and this junk is still here, please delete it :)
*/
#define OP_CALL_BOEHM_GC_ALLOC(size, r) OP_BOEHM_ZERO_MALLOC(size, r, 0, 0)

#endif /* USING_BOEHM_GC */

/* for no GC */
#ifdef USING_NO_GC

#undef OP_ZERO_MALLOC

#define OP_ZERO_MALLOC(size, r)  {                                 \
    r = (void*) malloc(size);                                  \
    if (r == NULL) { FAIL_EXCEPTION(PyExc_MemoryError, "out of memory"); } \
    else {                                                                  \
        memset((void*) r, 0, size);                                         \
        COUNT_MALLOC;                                                       \
    }                                                                       \
  }

#undef PUSH_ALIVE
#define PUSH_ALIVE(obj)

#endif /* USING_NO_GC */

/************************************************************/
/* rcpy support */

#define OP_CPY_MALLOC(cpytype, r)  {                            \
    /* XXX add tp_itemsize later */                             \
    OP_RAW_MALLOC(((PyTypeObject *)cpytype)->tp_basicsize, r);  \
    if (r) {                                                    \
        PyObject_Init((PyObject *)r, (PyTypeObject *)cpytype);  \
    }                                                           \
  }
#define OP_CPY_FREE(x)   OP_RAW_FREE(x)
