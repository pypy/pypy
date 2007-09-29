
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/

#define RAW_MALLOC_ZERO_FILLED 0

#if RAW_MALLOC_ZERO_FILLED

#define OP_RAW_MALLOC(size, r, restype)  {				\
		r = (restype) PyObject_Malloc(size);			\
		if (r != NULL) {					\
			memset((void*)r, 0, size);			\
			COUNT_MALLOC;					\
		}							\
	}

#else

#define OP_RAW_MALLOC(size, r, restype)  {				\
		r = (restype) PyObject_Malloc(size);			\
		if (r != NULL) {					\
			COUNT_MALLOC;					\
		} 							\
	}

#endif

#define OP_RAW_FREE(p, r) PyObject_Free(p); COUNT_FREE;

#define OP_RAW_MEMCLEAR(p, size, r) memset((void*)p, 0, size)

#define OP_RAW_MALLOC_USAGE(size, r) r = size

#ifdef MS_WINDOWS
#define alloca  _alloca
#endif

#ifdef USING_FRAMEWORK_GC
#define MALLOC_ZERO_FILLED 0
#else
#define MALLOC_ZERO_FILLED 1
#endif

#define OP_STACK_MALLOC(size,r,restype)                                 \
    r = (restype) alloca(size);                                         \
    if (r != NULL) memset((void*) r, 0, size);
    
#define OP_RAW_MEMCOPY(x,y,size,r) memcpy(y,x,size);

/************************************************************/

#define OP_FREE(p)	OP_RAW_FREE(p, do_not_use)

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

#define OP_BOEHM_ZERO_MALLOC(size, r, restype, is_atomic, is_varsize)   {             \
	r = (restype) BOEHM_MALLOC_ ## is_atomic ## _ ## is_varsize (size);    \
	if (r && is_atomic)  /* the non-atomic versions return cleared memory */ \
                memset((void*) r, 0, size);				\
  }

/* as we said in rbuiltin.py: 
# XXX this next little bit is a monstrous hack.  the Real Thing awaits
# some kind of proper GC integration
if GC integration has happened and this junk is still here, please delete it :)
*/
#define OP_CALL_BOEHM_GC_ALLOC(size, r) OP_BOEHM_ZERO_MALLOC(size, r, void *, 0, 0)

#define OP_BOEHM_DISAPPEARING_LINK(link, obj, r)			   \
	if (GC_base(obj) == NULL)					   \
		; /* 'obj' is probably a prebuilt object - it makes no */  \
		  /* sense to register it then, and it crashes Boehm in */ \
		  /* quite obscure ways */				   \
	else								   \
		GC_GENERAL_REGISTER_DISAPPEARING_LINK(link, obj)

#endif /* USING_BOEHM_GC */

/************************************************************/
/* rcpy support */

#define OP_CPY_MALLOC(cpytype, r, restype)  {				\
	/* XXX add tp_itemsize later */					\
	r = (restype)((PyTypeObject *)cpytype)->tp_alloc(		\
		(PyTypeObject *)cpytype, 0);				\
	if (!r) RPyConvertExceptionFromCPython();			\
    }
#define OP_CPY_FREE(x)   ((PyObject *)x)->ob_type->tp_free((PyObject *)x)

/************************************************************/
/* weakref support */

#define OP_CAST_PTR_TO_WEAKREFPTR(x, r)  r = x
#define OP_CAST_WEAKREFPTR_TO_PTR(x, r)  r = x
