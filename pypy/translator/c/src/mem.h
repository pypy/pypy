
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/

/* alignment for arena-based garbage collectors: the following line
   enforces an alignment that should be enough for any structure
   containing pointers and 'double' fields. */
struct rpy_memory_alignment_test1 {
  double d;
  void* p;
};
struct rpy_memory_alignment_test2 {
  char c;
  struct rpy_memory_alignment_test1 s;
};
#define MEMORY_ALIGNMENT	offsetof(struct rpy_memory_alignment_test2, s)
#define ROUND_UP_FOR_ALLOCATION(x)	\
		(((x) + (MEMORY_ALIGNMENT-1)) & ~(MEMORY_ALIGNMENT-1))

extern char __gcmapstart;
extern char __gcmapend;
extern char __gccallshapes;

#define PYPY_GCROOT(p)  asm ("/* GCROOT %0 */" : "=g" (p) : "0" (p) : "memory")
#define pypy_asm_gcroot(p) ({void*_r; \
               asm ("/* GCROOT %0 */" : "=g" (_r) : "0" (p) : "memory"); \
               _r; })

#define OP_LLVM_GCMAPSTART(r)	r = &__gcmapstart
#define OP_LLVM_GCMAPEND(r)	r = &__gcmapend
#define OP_LLVM_GCCALLSHAPES(r)	r = &__gccallshapes


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

void boehm_gc_startup_code(void);

#ifndef PYPY_NOT_MAIN_FILE
static void boehm_gc_finalizer_notifier(void)
{
	static int recursing = 0;
	if (recursing)
		return;  /* GC_invoke_finalizers() will be done by the
			    boehm_gc_finalizer_notifier() that is
			    currently in the C stack, when we return there */
	recursing = 1;
	while (GC_should_invoke_finalizers())
		GC_invoke_finalizers();
	recursing = 0;
}
void boehm_gc_startup_code(void)
{
	GC_init();
	GC_finalizer_notifier = &boehm_gc_finalizer_notifier;
	GC_finalize_on_demand = 1;
}
#endif /* PYPY_NOT_MAIN_FILE */

#endif /* USING_BOEHM_GC */

/************************************************************/
/* weakref support */

#define OP_CAST_PTR_TO_WEAKREFPTR(x, r)  r = x
#define OP_CAST_WEAKREFPTR_TO_PTR(x, r)  r = x
