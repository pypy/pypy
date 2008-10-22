
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
extern char __gcnoreorderhack;

/* The following pseudo-instruction is used by --gcrootfinder=asmgcc
   just after a call to tell gcc to put a GCROOT mark on each gc-pointer
   local variable.  All such local variables need to go through a "v =
   pypy_asm_gcroot(v)".  The old value should not be used any more by
   the C code; this prevents the following case from occurring: gcc
   could make two copies of the local variable (e.g. one in the stack
   and one in a register), pass one to GCROOT, and later use the other
   one.  In practice the pypy_asm_gcroot() is often a no-op in the final
   machine code and doesn't prevent most optimizations.  Getting the
   asm() right was tricky, though.  The asm() is not volatile so that
   gcc is free to delete it if the output variable is not used at all.
   We need to prevent gcc from moving the asm() *before* the call that
   could cause a collection; this is the purpose of the (unused)
   __gcnoreorderhack input argument.  Any memory input argument would
   have this effect: as far as gcc knows the call instruction can modify
   arbitrary memory, thus creating the order dependency that we want. */
#define pypy_asm_gcroot(p) ({void*_r; \
               asm ("/* GCROOT %0 */" : "=g" (_r) : \
                    "0" (p), "m" (__gcnoreorderhack)); \
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

#define OP_RAW_REALLOC_SHRINK(p, old_size, size, r) r = PyObject_Realloc((void*)p, size)

#define OP_RAW_REALLOC_GROW(p, old_size, size, r) r = PyObject_Realloc((void*)p, size)

#ifdef MS_WINDOWS
#define alloca  _alloca
#endif

#define OP_STACK_MALLOC(size,r,restype)                                 \
    r = (restype) alloca(size);                                         \
    if (r != NULL) memset((void*) r, 0, size);
    
#define OP_RAW_MEMCOPY(x,y,size,r) memcpy(y,x,size);
#define OP_RAW_MEMMOVE(x,y,size,r) memmove(y,x,size);

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

extern int boehm_gc_finalizer_lock;
void boehm_gc_startup_code(void);
void boehm_gc_finalizer_notifier(void);

#define OP_GC__DISABLE_FINALIZERS(r)  boehm_gc_finalizer_lock++
#define OP_GC__ENABLE_FINALIZERS(r)   (boehm_gc_finalizer_lock--,	\
				       boehm_gc_finalizer_notifier())

#ifndef PYPY_NOT_MAIN_FILE
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
#endif /* PYPY_NOT_MAIN_FILE */

#endif /* USING_BOEHM_GC */

/************************************************************/
/* weakref support */

#define OP_CAST_PTR_TO_WEAKREFPTR(x, r)  r = x
#define OP_CAST_WEAKREFPTR_TO_PTR(x, r)  r = x
