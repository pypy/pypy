
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/


#define GCSTRUCT_TO_STRUCT(typename, p)   (&(p)->data)

#define STRUCT_TO_GCSTRUCT(typename, p)   \
    ((typename##_gc*) (((char*)(p)) - offsetof(typename##_gc, data)))

#define REFCNT(typename, p)     STRUCT_TO_GCSTRUCT(typename, p)->refcount

/* ____________________________________________________________ */


#define OP_MALLOC(typename, r, err)  {                                  \
    typename##_gc *__block = (typename##_gc*) PyObject_Malloc(          \
                                                sizeof(typename##_gc)); \
    printf("allocated %d bytes at %p\n", sizeof(typename##_gc), __block); \
    if (__block == NULL) { PyErr_NoMemory(); FAIL(err) }                \
    __block->refcount = 1;                                              \
    r = GCSTRUCT_TO_STRUCT(typename, __block);                          \
    memset((void*) r, 0, sizeof(typename));                             \
  }

#define OP_MALLOC_VARSIZE(typename, vartypename, sizefield, nsize, r, err)  {  \
    size_t memsize = sizeof(typename##_gc) + (nsize-1)*sizeof(vartypename);    \
    typename##_gc *__block = (typename##_gc*) PyObject_Malloc(memsize);        \
    printf("var-allocated %d bytes at %p\n", memsize, __block); \
    if (__block == NULL) { PyErr_NoMemory(); FAIL(err) }                       \
    memset((void*) __block, 0, memsize);                                       \
    __block->refcount = 1;                                                     \
    r = GCSTRUCT_TO_STRUCT(typename, __block);                                 \
    r->sizefield = nsize;                                                      \
  }
#define STRUCTFREE(typename, p) {                               \
    printf("freeing %p\n", STRUCT_TO_GCSTRUCT(typename, p));    \
    PyObject_Free(STRUCT_TO_GCSTRUCT(typename, p));             \
  }


#define OP_GETFIELD(x, fieldname, r, err)         r = x->fieldname;
#define OP_SETFIELD(x, fieldname, val, r, err)    x->fieldname = val;
#define OP_GETSUBSTRUCT(x, fieldname, r, err)     r = &x->fieldname;
