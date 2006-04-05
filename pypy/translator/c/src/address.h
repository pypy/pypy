/************************************************************/
/***  C header subsection: operations between addresses   ***/

/*** unary operations ***/

/***  binary operations ***/

#define OP_ADR_DELTA(x,y,r) r = ((char *)(x) - (char *)(y))
#define OP_ADR_SUB(x,y,r)   r = ((char *)(x) - (y))
#define OP_ADR_ADD(x,y,r)   r = ((char *)(x) + (y))

#define OP_ADR_EQ(x,y,r)	  r = ((x) == (y))
#define OP_ADR_NE(x,y,r)	  r = ((x) != (y))
#define OP_ADR_LE(x,y,r)	  r = ((x) <= (y))
#define OP_ADR_GT(x,y,r)	  r = ((x) >  (y))
#define OP_ADR_LT(x,y,r)	  r = ((x) <  (y))
#define OP_ADR_GE(x,y,r)	  r = ((x) >= (y))

#define OP_RAW_MALLOC(size,r)                                          \
    r = (void*) calloc(1, size);                                       \
    if (r == NULL) FAIL_EXCEPTION( PyExc_MemoryError, "out of memory");\

#ifdef MS_WINDOWS
#define alloca  _alloca
#endif

#define OP_STACK_MALLOC(size,r)                                            \
    r = (void*) alloca(size);                                              \
    if (r == NULL) FAIL_EXCEPTION(PyExc_MemoryError, "out of memory");\
 
#define OP_RAW_FREE(x,r)        free(x);
#define OP_RAW_MEMCOPY(x,y,size,r) memcpy(y,x,size);

