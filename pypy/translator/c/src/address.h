/************************************************************/
/***  C header subsection: operations between addresses   ***/

/*** unary operations ***/

/***  binary operations ***/

#define OP_ADR_DELTA(x,y,r,err) r = ((x) - (y))
#define OP_ADR_SUB(x,y,r,err)   r = ((x) - (y))
#define OP_ADR_ADD(x,y,r,err)   r = ((x) + (y))

#define OP_ADR_EQ(x,y,r,err)	  r = ((x) == (y))
#define OP_ADR_NE(x,y,r,err)	  r = ((x) != (y))
#define OP_ADR_LE(x,y,r,err)	  r = ((x) <= (y))
#define OP_ADR_GT(x,y,r,err)	  r = ((x) >  (y))
#define OP_ADR_LT(x,y,r,err)	  r = ((x) <  (y))
#define OP_ADR_GE(x,y,r,err)	  r = ((x) >= (y))

#define OP_RAW_MALLOC(size,r,err)                                           \
    r = (void*) malloc(size);                                              \
    if (r == NULL) FAIL_EXCEPTION(err, PyExc_MemoryError, "out of memory");\
 
#define OP_RAW_FREE(x,r,err)        free(x);
#define OP_RAW_MEMCOPY(x,y,size,r,err) memcpy(y,x,size);
